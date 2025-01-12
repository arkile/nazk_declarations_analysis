def try_socket():
    import socket

    HOST = 'www.google.com'  # Server hostname or IP address
    PORT = 80  # The standard port for HTTP is 80, for HTTPS it is 443

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (HOST, PORT)
    client_socket.connect(server_address)

    request_header = b'GET / HTTP/1.0\r\nHost: www.google.com\r\n\r\n'
    client_socket.sendall(request_header)

    response = ''
    while True:
        recv = client_socket.recv(1024)
        if not recv:
            break
        response += recv.decode('utf-8')

    print(response)
    client_socket.close()


def try_urllib3():
    import urllib3
    http = urllib3.PoolManager()
    r = http.request('GET', 'http://www.google.com')
    print(r.data)


def try_lxml():
    import urllib3
    http = urllib3.PoolManager()
    r = http.request('GET', 'http://www.google.com')
    # print(r.data)

    # ... Previous snippet here
    from lxml import html

    # We reuse the response from urllib3
    data_string = r.data.decode('utf-8', errors='ignore')

    # We instantiate a tree object from the HTML
    tree = html.fromstring(data_string)

    # We run the XPath against this HTML
    # This returns an array of elements
    links = tree.xpath('//a')

    for link in links:
        # For each element we can easily get back the URL
        print(link.get('href'))


def try_requests_image():
    import requests

    url = 'https://www.google.com/images/branding/googlelogo/1x/googlelogo_light_color_272x92dp.png'
    response = requests.get(url)
    with open('image.jpg', 'wb') as file:
        file.write(response.content)


def try_beautiful_soup():
    import requests
    from bs4 import BeautifulSoup

    BASE_URL = 'https://news.ycombinator.com'
    USERNAME = "user_120624"
    PASSWORD = "password_120624"

    s = requests.Session()

    data = {"goto": "news", "acct": USERNAME, "pw": PASSWORD}
    r = s.post(f'{BASE_URL}/login', data=data)

    soup = BeautifulSoup(r.text, 'html.parser')
    if soup.find(id='logout') is not None:
        print('Successfully logged in')
    else:
        print('Authentication Error')


def try_beautiful_soup2():
    import requests
    from bs4 import BeautifulSoup

    r = requests.get('https://news.ycombinator.com')
    soup = BeautifulSoup(r.text, 'html.parser')
    links = soup.findAll('tr', class_='athing')

    formatted_links = []

    for link in links:
        data = {
            'id': link['id'],
            'title': link.find_all('td')[2].a.text,
            "url": link.find_all('td')[2].a['href'],
            "rank": int(link.find_all('td')[0].span.text.replace('.', ''))
        }
        formatted_links.append(data)

    print(formatted_links)


def try_save_csv_file():
    import csv

    # Sample data
    data = [
        {'id': '1', 'title': 'Post 1', 'url': 'http://example.com/1', 'rank': 1},
        {'id': '2', 'title': 'Post 2', 'url': 'http://example.com/2', 'rank': 2}
    ]

    # Define the CSV file path
    csv_file = 'hacker_news_posts.csv'

    # Write data to CSV
    with open(csv_file, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['id', 'title', 'url', 'rank'])
        writer.writeheader()
        for row in data:
            writer.writerow(row)
