from datetime import datetime, timedelta
from typing import Dict, Optional, List
from enum import Enum
import re

class PaymentProvider(Enum):
    ORANGE_MONEY = "Orange Money"
    MOOV_MONEY = "Moov Money"
    WAVE = "Wave"

class PaymentVerification:
    def __init__(self):
        # In a real app, this would be a database
        self.payments: Dict[str, dict] = {}
        self.payment_codes: Dict[str, str] = {}
        self.phone_numbers = {
            PaymentProvider.ORANGE_MONEY: "+22604647641",
            PaymentProvider.MOOV_MONEY: "+22601256984",
            PaymentProvider.WAVE: "+22558485509"
        }

    def generate_transaction_code(self, provider: PaymentProvider) -> str:
        """Generate a transaction code for the given provider"""
        prefix = {
            PaymentProvider.ORANGE_MONEY: "OM",
            PaymentProvider.MOOV_MONEY: "MV",
            PaymentProvider.WAVE: "WV"
        }.get(provider, "TX")
        
        import random
        code = f"{prefix}{random.randint(100000, 999999)}"
        return code

    def verify_transaction_code(self, code: str, amount: float) -> bool:
        """Verify if a transaction code is valid and payment was received"""
        # In a real implementation, you would check your mobile money account
        # Here we'll just check if the code exists in our records
        return code in self.payment_codes and self.payment_codes[code]["amount"] == amount

    def record_payment(self, amount: float, provider: PaymentProvider, phone_number: str) -> str:
        """Record a new payment and return a transaction code"""
        code = self.generate_transaction_code(provider)
        self.payment_codes[code] = {
            "amount": amount,
            "provider": provider,
            "phone_number": phone_number,
            "timestamp": datetime.now(),
            "verified": False
        }
        return code

    def get_payment_instructions(self, provider: PaymentProvider) -> str:
        """Get payment instructions for the user"""
        instructions = {
            PaymentProvider.ORANGE_MONEY: (
                f"Faites un paiement Orange Money au {self.phone_numbers[PaymentProvider.ORANGE_MONEY]} "
                "et entrez le code de transaction reçu."
            ),
            PaymentProvider.MOOV_MONEY: (
                f"Faites un paiement Moov Money au {self.phone_numbers[PaymentProvider.MOOV_MONEY]} "
                "et entrez le code de transaction reçu."
            ),
            PaymentProvider.WAVE: (
                f"Faites un paiement Wave au {self.phone_numbers[PaymentProvider.WAVE]} "
                "et entrez le code de transaction reçu."
            )
        }
        return instructions.get(provider, "Paiement non supporté.")

    def get_supported_providers(self) -> List[Dict[str, str]]:
        """Get list of supported payment providers"""
        return [
            {"name": provider.value, "number": self.phone_numbers[provider]}
            for provider in PaymentProvider
        ]

# Example usage
if __name__ == "__main__":
    payment_system = PaymentVerification()
    
    # Example: User wants to pay with Orange Money
    provider = PaymentProvider.ORANGE_MONEY
    amount = 1000  # FCFA
    
    # Generate a transaction code for the user
    transaction_code = payment_system.record_payment(
        amount=amount,
        provider=provider,
        phone_number="+22670123456"  # User's phone number
    )
    
    print(f"Instructions: {payment_system.get_payment_instructions(provider)}")
    print(f"Code de transaction: {transaction_code}")
    
    # Later, when verifying the payment
    is_verified = payment_system.verify_transaction_code(transaction_code, amount)
    print(f"Paiement vérifié: {'Oui' if is_verified else 'Non'}")
