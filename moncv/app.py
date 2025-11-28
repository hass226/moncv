from flask import Flask, render_template, request, jsonify, redirect, url_for
from payment_verification import PaymentVerification, PaymentProvider

app = Flask(__name__)
payment_system = PaymentVerification()

@app.route('/')
def home():
    return render_template('index.html', providers=payment_system.get_supported_providers())

@app.route('/initiate_payment', methods=['POST'])
def initiate_payment():
    data = request.form
    try:
        amount = float(data.get('amount'))
        provider = PaymentProvider(data.get('provider'))
        phone_number = data.get('phone_number')
        
        transaction_code = payment_system.record_payment(
            amount=amount,
            provider=provider,
            phone_number=phone_number
        )
        
        return jsonify({
            'success': True,
            'transaction_code': transaction_code,
            'instructions': payment_system.get_payment_instructions(provider)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/verify_payment', methods=['POST'])
def verify_payment():
    data = request.form
    try:
        transaction_code = data.get('transaction_code')
        amount = float(data.get('amount'))
        
        is_verified = payment_system.verify_transaction_code(transaction_code, amount)
        
        return jsonify({
            'success': True,
            'verified': is_verified
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)
