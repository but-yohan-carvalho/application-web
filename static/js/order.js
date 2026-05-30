function showError(message) {
    const alert = document.getElementById('error-alert');
    alert.textContent = message;
    alert.classList.add('visible');
    alert.scrollIntoView({ behavior: 'smooth' });
}

const shippingForm = document.getElementById('shipping-form');
if (shippingForm) {
    shippingForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = shippingForm.querySelector('[type=submit]');
        btn.disabled = true;
        btn.textContent = 'Envoi en cours...';

        const body = {
            order: {
                email: document.getElementById('email').value,
                shipping_information: {
                    address: document.getElementById('address').value,
                    city: document.getElementById('city').value,
                    province: document.getElementById('province').value,
                    postal_code: document.getElementById('postal-code').value,
                    country: document.getElementById('country').value,
                }
            }
        };

        try {
            const res = await fetch(`/order/${ORDER_ID}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            if (res.ok) {
                window.location.reload();
            } else {
                const data = await res.json();
                showError(data.errors?.order?.name || 'Erreur inconnue');
                btn.disabled = false;
                btn.textContent = 'Continuer vers le paiement →';
            }
        } catch (err) {
            showError('Erreur réseau. Veuillez réessayer.');
            btn.disabled = false;
            btn.textContent = 'Continuer vers le paiement →';
        }
    });
}

const paymentForm = document.getElementById('payment-form');
if (paymentForm) {
    paymentForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('pay-btn');
        btn.disabled = true;
        btn.textContent = 'Traitement en cours...';

        const ccNumber = document.getElementById('cc-number').value.replace(/\s/g, '');

        const body = {
            credit_card: {
                name: document.getElementById('cc-name').value,
                number: ccNumber,
                expiration_year: parseInt(document.getElementById('cc-year').value),
                expiration_month: parseInt(document.getElementById('cc-month').value),
                cvv: document.getElementById('cc-cvv').value,
            }
        };

        try {
            const res = await fetch(`/order/${ORDER_ID}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            if (res.ok) {
                window.location.reload();
            } else {
                const data = await res.json();
                const msg = data.errors?.order?.name || data.errors?.credit_card?.name || 'Paiement refusé';
                showError(msg);
                btn.disabled = false;
                btn.textContent = 'Réessayer';
            }
        } catch (err) {
            showError('Erreur réseau. Veuillez réessayer.');
            btn.disabled = false;
            btn.textContent = 'Réessayer';
        }
    });
}
