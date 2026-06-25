// Panier client (localStorage) — partagé sur toutes les pages.
(function () {
    const KEY = 'inf349_cart';

    const get = () => JSON.parse(localStorage.getItem(KEY) || '[]');
    const save = (cart) => {
        localStorage.setItem(KEY, JSON.stringify(cart));
        render();
    };

    function add(item) {
        const cart = get();
        const existing = cart.find((p) => p.id === item.id);
        if (existing) existing.quantity += item.quantity;
        else cart.push(item);
        save(cart);
        show();
    }

    function setQty(id, qty) {
        let cart = get();
        if (qty <= 0) {
            cart = cart.filter((p) => p.id !== id);
        } else {
            const it = cart.find((p) => p.id === id);
            if (it) it.quantity = qty;
        }
        save(cart);
    }

    const count = () => get().reduce((n, p) => n + p.quantity, 0);
    const subtotal = () => get().reduce((s, p) => s + p.price * p.quantity, 0);

    function render() {
        const badge = document.getElementById('cart-badge');
        if (badge) badge.textContent = count();

        const box = document.getElementById('cart-items');
        if (box) {
            const cart = get();
            if (!cart.length) {
                box.innerHTML = '<p style="color:#888;text-align:center;margin-top:40px;">Votre panier est vide.</p>';
            } else {
                box.innerHTML = cart.map((p) => `
                    <div class="cart-row" data-id="${p.id}"
                         style="display:flex;gap:12px;align-items:center;padding:12px 0;border-bottom:1px solid #f0f0f0;">
                        <img src="${(window.IMAGE_BASE || '')}${p.image}" alt=""
                             style="width:56px;height:56px;object-fit:cover;border-radius:8px;background:#f5f5f5;flex-shrink:0;">
                        <div style="flex:1;min-width:0;">
                            <div style="font-weight:700;font-size:0.9rem;">${p.name}</div>
                            <div style="color:#888;font-size:0.82rem;">$${(p.price / 100).toFixed(2)}</div>
                        </div>
                        <div style="display:flex;align-items:center;gap:8px;">
                            <button class="cq-minus" style="width:28px;height:28px;border:1px solid #ddd;background:#fff;border-radius:6px;cursor:pointer;">−</button>
                            <span style="min-width:18px;text-align:center;">${p.quantity}</span>
                            <button class="cq-plus" style="width:28px;height:28px;border:1px solid #ddd;background:#fff;border-radius:6px;cursor:pointer;">+</button>
                        </div>
                    </div>`).join('');
            }
        }

        const sub = document.getElementById('cart-subtotal');
        if (sub) sub.textContent = '$' + (subtotal() / 100).toFixed(2);
    }

    let oc;
    function show() {
        const el = document.getElementById('cartOffcanvas');
        if (el && window.bootstrap) {
            oc = oc || new bootstrap.Offcanvas(el);
            oc.show();
        }
    }

    async function checkout() {
        const cart = get();
        if (!cart.length) return;

        const btn = document.getElementById('cart-checkout');
        btn.disabled = true;
        btn.textContent = 'CHARGEMENT...';

        try {
            const res = await fetch('/order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    products: cart.map((p) => ({ id: p.id, quantity: p.quantity })),
                }),
            });

            if (res.ok || res.redirected) {
                localStorage.removeItem(KEY);
                window.location.href = res.url;
            } else {
                const data = await res.json().catch(() => ({}));
                alert((data.errors && data.errors.product && data.errors.product.name) || 'Erreur lors de la commande');
                btn.disabled = false;
                btn.textContent = 'PASSER LA COMMANDE';
            }
        } catch (err) {
            alert('Erreur réseau. Veuillez réessayer.');
            btn.disabled = false;
            btn.textContent = 'PASSER LA COMMANDE';
        }
    }

    // Délégation d'événements (les boutons produits sont rendus par le serveur).
    document.addEventListener('click', (e) => {
        const addBtn = e.target.closest('.add-cart-btn');
        if (addBtn) {
            const row = addBtn.closest('.product-order-row');
            const qty = row ? (parseInt(row.querySelector('.qty-input').value) || 1) : 1;
            add({
                id: parseInt(addBtn.dataset.id),
                name: addBtn.dataset.name,
                price: parseInt(addBtn.dataset.price),
                image: addBtn.dataset.image,
                quantity: qty,
            });
            return;
        }

        const toggle = e.target.closest('#cart-toggle');
        if (toggle) {
            e.preventDefault();
            render();
            show();
            return;
        }

        if (e.target.closest('#cart-checkout')) {
            checkout();
            return;
        }

        const minus = e.target.closest('.cq-minus');
        if (minus) {
            const id = parseInt(minus.closest('.cart-row').dataset.id);
            const it = get().find((p) => p.id === id);
            setQty(id, (it ? it.quantity : 1) - 1);
            return;
        }

        const plus = e.target.closest('.cq-plus');
        if (plus) {
            const id = parseInt(plus.closest('.cart-row').dataset.id);
            const it = get().find((p) => p.id === id);
            setQty(id, (it ? it.quantity : 1) + 1);
        }
    });

    document.addEventListener('DOMContentLoaded', render);
})();
