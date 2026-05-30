document.querySelectorAll('.commander-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
        const productId = parseInt(btn.dataset.productId);
        const wrap = btn.closest('.product-order-row');
        const qty = parseInt(wrap.querySelector('.qty-input').value) || 1;

        btn.disabled = true;
        btn.textContent = 'CHARGEMENT...';

        try {
            const res = await fetch('/order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ product: { id: productId, quantity: qty } })
            });

            if (res.ok || res.redirected) {
                window.location.href = res.url;
            } else {
                const data = await res.json();
                const msg = data.errors?.product?.name || 'Erreur lors de la commande';
                const errEl = document.getElementById('order-error');
                errEl.textContent = msg;
                errEl.classList.add('visible');
                btn.disabled = false;
                btn.textContent = 'COMMANDER';
            }
        } catch (err) {
            const errEl = document.getElementById('order-error');
            errEl.textContent = 'Erreur réseau. Veuillez réessayer.';
            errEl.classList.add('visible');
            btn.disabled = false;
            btn.textContent = 'COMMANDER';
        }
    });
});
