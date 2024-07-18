# fastapi-auth-wss

This is a detailed guide on how to set up and use the Chat System. Please follow the instructions below to get started.

## Requirements

Before proceeding, make sure you have the following requirements installed:

- Python 3.x
- FastAPI
- PieSocket

You can install the required dependencies by running the following command:

```shell
pip install -r requirements.txt
```

## Running the Server

To run the server, use the following command:

```shell
uvicorn main:app --reload
```

OR

```shell
fastapi run
```

Once the server is running, you can access the Swagger UI by navigating to `/docs` in your web browser.

## Using Swagger UI

Swagger UI provides a user-friendly interface to test the APIs of the Chat System. Follow the steps below to use Swagger UI effectively:

1. Register Yourself: To register as a user, navigate to the `/register` endpoint and provide the required information.

2. Obtain Token: After registering, go to the token route to obtain a token. This token will be used for authentication.

3. Open Multiple Instances of PieSocket: Open two different tabs in your web browser and paste the following WebSocket URLs:

    - `ws://ip_address:8000/ws/channel_name/jwt_token1`
    - `ws://ip_address:8000/ws/channel_name/jwt_token2`

    Replace `ip_address` with your localhost IP, `channel_name` with the desired channel name and `jwt_token1` and `jwt_token2` with the tokens obtained in step 2.

4. Start Chatting: Once the WebSocket connections are established, you can start chatting between the two instances of PieSocket.

That's it! You are now ready to use the Chat System. Enjoy chatting!
