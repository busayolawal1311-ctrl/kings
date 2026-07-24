/**
 * Progressive-enhancement interactions for the storefront.
 *
 * The server remains authoritative for cart state and pricing. JavaScript only
 * improves responsiveness; pages remain usable for navigation and forms without it.
 */
(() => {
  /** Read Django's CSRF cookie before issuing a state-changing fetch request. */
  const getCookie = (name) => document.cookie.split('; ').find((row) => row.startsWith(`${name}=`))?.split('=')[1];

  /** Announce ephemeral success/error feedback to assistive technology and sighted users. */
  const toast = (message) => {
    const node = document.createElement('div');
    node.className = 'toast';
    node.textContent = message;
    document.querySelector('.toast-region').append(node);
    setTimeout(() => node.remove(), 3600);
  };

  /** Keep every cart badge in sync after a server-confirmed mutation. */
  const setCount = (count) => document.querySelectorAll('[data-cart-count]').forEach((node) => { node.textContent = count || '0'; });

 /**
   * Submit URL-encoded data with Django's CSRF token.
   * Rejecting non-2xx responses prevents the UI from falsely claiming a cart update.
   */
  const post = async (url, data = {}) => {
    // Grab the token from the meta tag we added to mainlayout.html
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken,
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams(data),
    });
    if (!response.ok) throw new Error('Request failed');
    return response.json();
  };

  // Mobile navigation keeps its expanded state exposed to screen readers.
  document.querySelector('[data-menu-toggle]')?.addEventListener('click', (event) => {
    const navigation = document.querySelector('.primary-nav');
    const open = navigation.classList.toggle('is-open');
    event.currentTarget.setAttribute('aria-expanded', open);
  });

  // The promotion can be dismissed without affecting page content or focus order.
  document.querySelector('[data-dismiss-announcement]')?.addEventListener('click', () => document.querySelector('[data-announcement]').remove());

  // Size choices behave as a single-selection control until variants are wired to inventory.
  document.querySelectorAll('.size-choice').forEach((button) => button.addEventListener('click', () => {
    button.parentElement.querySelectorAll('button').forEach((item) => item.setAttribute('aria-pressed', item === button));
  }));

  // Product-page quantity is capped client-side for feedback; the server also validates it.
  let quantity = 1;
  const quantityOutput = document.querySelector('[data-quantity]');
  document.querySelector('[data-quantity-minus]')?.addEventListener('click', () => { quantity = Math.max(1, quantity - 1); quantityOutput.textContent = quantity; });
  document.querySelector('[data-quantity-plus]')?.addEventListener('click', () => { quantity = Math.min(99, quantity + 1); quantityOutput.textContent = quantity; });

  // Add-to-bag requests use the server response as the only source for the new count.
  document.querySelectorAll('.add-to-cart').forEach((button) => button.addEventListener('click', async () => {
    button.disabled = true;
    const originalLabel = button.textContent;
    button.textContent = 'Adding…';
    try {
      const result = await post(button.dataset.cartUrl, { quantity: button.hasAttribute('data-quantity-source') ? quantity : 1 });
      setCount(result.count);
      toast(result.message);
    } catch {
      toast('We could not update your bag. Please try again.');
    } finally {
      button.disabled = false;
      button.textContent = originalLabel;
    }
  }));

  // Cart rows update independently, avoiding a costly full-page reload for quantity changes.
  document.querySelectorAll('[data-cart-item]').forEach((item) => {
    const output = item.querySelector('[data-cart-quantity]');
    const update = async (amount) => {
      const nextQuantity = Math.max(0, Number(output.textContent) + amount);
      try {
        const result = await post(item.dataset.updateUrl, { quantity: nextQuantity });
        setCount(result.count);
        if (!nextQuantity) item.remove(); else output.textContent = nextQuantity;
        toast(result.message);
      } catch {
        toast('We could not update your bag.');
      }
    };
    item.querySelector('[data-cart-minus]')?.addEventListener('click', () => update(-1));
    item.querySelector('[data-cart-plus]')?.addEventListener('click', () => update(1));
    item.querySelector('.remove-cart-item')?.addEventListener('click', () => update(-Number(output.textContent)));
  });

  // These messages keep unsupported provider integrations explicit instead of silently failing.
  document.querySelector('[data-promo]')?.addEventListener('click', () => toast('Promo codes are applied during secure checkout.'));
  document.querySelector('[data-checkout]')?.addEventListener('click', () => toast('Checkout is ready to connect to your payment provider.'));
})();
