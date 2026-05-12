from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return "L'API de paiement est en ligne !"

@app.route('/test-api', methods=['GET'])
def test_api():
    return jsonify({
        "status": "success",
        "message": "Connexion à l'API réussie"
    })

if __name__ == '__main__':
    app.run(debug=True)