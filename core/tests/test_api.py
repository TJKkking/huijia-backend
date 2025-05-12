import requests
import json
import traceback

BASE_URL = "http://localhost:8000/api/v1/"

def print_response(resp, operation_name):
    print(f"\n=== {operation_name} ===")
    print(f"URL: {resp.url}")
    print(f"Method: {resp.request.method}")
    print(f"Request Headers: {dict(resp.request.headers)}")
    if resp.request.body:
        print(f"Request Body: {resp.request.body}")
    print(f"Status Code: {resp.status_code}")
    print(f"Response Headers: {dict(resp.headers)}")
    print(f"Response Text: {resp.text}")
    try:
        data = resp.json()
        print(f"Response JSON: {json.dumps(data, indent=2, ensure_ascii=False)}")
        if 'detail' in data:
            print(f"🔍 Error Detail: {data['detail']}")
        elif 'non_field_errors' in data:
            print(f"🔍 Non-field Errors: {data['non_field_errors']}")
    except json.JSONDecodeError:
        print("Response is not JSON format")

def login(username, password):
    url = "http://localhost:8000/api/token/"
    resp = requests.post(url, data={'username': username, 'password': password})
    print_response(resp, "Login")
    resp.raise_for_status()
    return resp.json()['access']

def get_users(token):
    url = BASE_URL + "users/"
    resp = requests.get(url, headers={'Authorization': f'Bearer {token}'})
    print_response(resp, "Get Users")
    resp.raise_for_status()

def create_post(token, title, content):
    url = BASE_URL + "posts/"
    data = {
        "title": title,
        "content": content,
        "status": "published"
    }
    resp = requests.post(url, json=data, headers={'Authorization': f'Bearer {token}'})
    print_response(resp, "Create Post")
    resp.raise_for_status()
    return resp.json()['id']

def get_posts(token):
    url = BASE_URL + "posts/"
    resp = requests.get(url, headers={'Authorization': f'Bearer {token}'})
    print_response(resp, "Get Posts")
    resp.raise_for_status()

def add_comment(token, post_id, content):
    url = BASE_URL + f"posts/{post_id}/comments/"
    data = {
        "content": content,
        "post": post_id
    }
    resp = requests.post(url, json=data, headers={'Authorization': f'Bearer {token}'})
    print_response(resp, "Add Comment")
    resp.raise_for_status()
    return resp.json()['id']

def get_comments(token, post_id):
    url = BASE_URL + f"posts/{post_id}/comments/"
    resp = requests.get(url, headers={'Authorization': f'Bearer {token}'})
    print_response(resp, "Get Comments")
    resp.raise_for_status()

def like_post(token, post_id):
    url = BASE_URL + f"posts/{post_id}/like/"
    resp = requests.post(url, headers={'Authorization': f'Bearer {token}'})
    print_response(resp, "Like Post")
    resp.raise_for_status()

def get_notifications(token):
    url = BASE_URL + "notifications/"
    resp = requests.get(url, headers={'Authorization': f'Bearer {token}'})
    print_response(resp, "Get Notifications")
    resp.raise_for_status()

if __name__ == "__main__":
    try:
        token = login('common', 'common')
        get_users(token)
        post_id = create_post(token, "测试标题", "测试内容")
        get_posts(token)
        comment_id = add_comment(token, post_id, "这是一条评论")
        get_comments(token, post_id)
        like_post(token, post_id)
        get_notifications(token)

    except requests.exceptions.RequestException as e:
        print(f"\n📛 Request Error: {str(e)}")
        traceback.print_exc()
    except Exception as e:
        print(f"\n❗ Unexpected Error: {str(e)}")
        traceback.print_exc()
