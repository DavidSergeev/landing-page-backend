from src.agent_tools.http_tools import http_request

def main():
    response = http_request("https://il.flightnetwork.com/rf/start")
    pass

if __name__ == "__main__":
    main()