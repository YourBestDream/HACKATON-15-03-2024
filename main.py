from server import create_app

app = create_app()

if __name__ == '__main__':
    # app.run(host = '0.0.0.0', port = 5000, debug = True, ssl_context = ('E:\programs\SSL_certificates\server.crt', 'E:\programs\SSL_certificates\server.key'))
    app.run(host = '0.0.0.0', port = 5000, debug = True)