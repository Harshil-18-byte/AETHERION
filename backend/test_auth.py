import requests

def test_register():
    print("Testing signup...")
    try:
        r = requests.post("http://localhost:8000/auth/register", json={
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "testpassword123"
        })
        print(r.status_code, r.text)

        print("Testing login...")
        r = requests.post("http://localhost:8000/auth/login", data={
            "username": "test@example.com",
            "password": "testpassword123"
        })
        print(r.status_code, r.text)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_register()
