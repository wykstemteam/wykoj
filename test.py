from wykoj import create_app

app = create_app(test=True)
app.run(port=4000, debug=True)
