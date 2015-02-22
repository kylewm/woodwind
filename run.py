#!/usr/bin/env python


def main():
    from woodwind.app import create_app
    app = create_app()
    app.run(debug=True, port=4000)


main()
