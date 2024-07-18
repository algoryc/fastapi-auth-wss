from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import aioredis as redis
import asyncio
import json
from . import crud, models, schema
from .database import SessionLocal, engine

# JWT settings
SECRET_KEY = "1893"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()

models.Base.metadata.create_all(bind=engine)

r = redis.from_url('redis://localhost:6379', decode_responses=True)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, channel_name: str, username: str) -> None:
        await websocket.accept()
        if channel_name not in self.active_connections:
            self.active_connections[channel_name] = {}
        self.active_connections[channel_name][username] = websocket

    def disconnect(self, channel_name: str, username: str) -> None:
        del self.active_connections[channel_name][username]
        if not self.active_connections[channel_name]:
            del self.active_connections[channel_name]

manager = ConnectionManager()

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str, db: Session):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schema.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = crud.get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

@app.post("/register", response_model=schema.UserInDB)
def register(user: schema.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)

@app.post("/token", response_model=schema.Token)
async def login_for_access_token(form_data: schema.UserToken, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.websocket("/ws/{channel_name}/{token}")
async def websocket_endpoint(
    websocket: WebSocket,
    channel_name: str,
    token: str,
    db: Session = Depends(get_db)
):
    try:
        user = await get_current_user(token, db)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, channel_name, user.username)
    pubsub = r.pubsub()
    await pubsub.subscribe(channel_name)

    try:
        while True:
            done, pending = await asyncio.wait(
                [websocket.receive_text(), pubsub.get_message()],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for task in done:
                if task.result() is None:
                    continue
                
                if isinstance(task.result(), dict):  # This is a message from Redis
                    message = task.result()
                    if message['type'] == 'message':
                        data = json.loads(message['data'])
                        if data['username'] != user.username:
                            await websocket.send_text(json.dumps(data))
                else:  # This is a message from WebSocket
                    data = task.result()
                    message = json.dumps({"username": user.username, "message": data})
                    await r.publish(channel_name, message)
            
            for task in pending:
                task.cancel()
    
    except WebSocketDisconnect:
        manager.disconnect(channel_name, user.username)
        await pubsub.unsubscribe(channel_name)

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="192.168.18.41", port=8000)