if __name__ == '__main__':
    from openport.apps.openport_app import OpenportApp
    app = OpenportApp()
    app.parse_args()
    app.start()
