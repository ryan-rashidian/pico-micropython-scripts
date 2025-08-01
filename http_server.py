from time import sleep, ticks_diff, ticks_ms # type: ignore
import network # type: ignore
import socket
import asyncio
from machine import Pin # type: ignore

led = Pin('WL_GPIO0', Pin.OUT)

wlan = network.WLAN(network.STA_IF)
server = socket.socket()
server.setblocking(False)

start_time = ticks_ms()

running = True

async def _serve_http():
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    server.bind(addr)
    server.listen(1)
    start_time = ticks_ms()
    print(f'HTTP server listening on: {addr}')

    global running
    while running:
        try:
            conn, addr = server.accept()
            print(f'Client connected: {addr}')
            # Read and discard HTTP request
            conn.setblocking(True)
            try:
                _ = conn.recv(1024)
            except Exception:
                conn.close()
                continue

            uptime_ms = ticks_diff(ticks_ms(), start_time)
            uptime_sec = uptime_ms // 1000
            rssi = wlan.status('rssi')
            message = """\
            One ought to hold on to one's heart; for if one lets it go,
            one soon loses control of the head too.
            Alas, where in the world has there been more folly than among the pitying?
            And what in the world has caused more suffering than the folly of the pitying?
            Woe to all who love without having a height that is above their pity!
            \n
            Thus spoke the devil to me once: 
            "God too has his hell: that is his love of man."
            \n
            And most recently I heard him say this:
            "God is dead: God died of his pity for man."
            \n
            - Thus spoke Zarathustra.
            """

            try:
                with open('index.html', 'r') as f:
                    html = f.read()
                    html = html.replace('{{rssi}}', str(rssi))
                    html = html.replace('{{uptime_sec}}', str(uptime_sec))
                    html = html.replace('{{message}}', message)
            except OSError:
                html = "<h1>File not found</h1>"

            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/html\r\n"
                "\r\n"
                f"{html}"
            )
            
            conn.send(response.encode())
            conn.close()
            for _ in range(10):
                led.toggle()
                await asyncio.sleep(0.1)
        except OSError:
            led.toggle()
            await asyncio.sleep(1)
            continue

def _stop_server():
    global running
    running = False

async def connect(ssid, password):
    wlan.active(True)
    # Disable 'Power Saving Mode'
    wlan.config(pm=0xa11140)
    led.on()

    if not wlan.isconnected():
        wlan.connect(ssid, password)
        print('Connecting to network...')

        for _ in range(30):
            if wlan.isconnected():
                print(f'Connected to Wifi network: {ssid}')
                break
            await asyncio.sleep(0.5)

    if wlan.isconnected():
        led.off()
        print('Network config:', wlan.ifconfig())
        asyncio.create_task(_serve_http())

    else:
        print('Connection failed.')
        led.off()

def disconnect():
    _stop_server()
    try:
        server.close()
    except Exception:
        pass

    wlan.disconnect()
    wlan.active(False)
    led.off()
    sleep(0.5)

