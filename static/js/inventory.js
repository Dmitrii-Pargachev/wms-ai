/**
 * WMS-AI Inventory Module
 */

const API = {
    // Categories
    async getCategories() {
        const res = await fetch('/api/categories/');
        return res.json();
    },

    async createCategory(data) {
        const res = await fetch('/api/categories/create/', {
            method: 'POST',
            headers: this.headers(),
            body: JSON.stringify(data),
        });
        return res.json();
    },

    // Suppliers
    async getSuppliers(search = '') {
        const res = await fetch(`/api/suppliers/?search=${encodeURIComponent(search)}`);
        return res.json();
    },

    async createSupplier(data) {
        const res = await fetch('/api/suppliers/create/', {
            method: 'POST',
            headers: this.headers(),
            body: JSON.stringify(data),
        });
        return res.json();
    },

    // Products
    async getProducts(params = {}) {
        const query = new URLSearchParams(params).toString();
        const res = await fetch(`/api/products/?${query}`);
        return res.json();
    },

    async createProduct(data) {
        const res = await fetch('/api/products/create/', {
            method: 'POST',
            headers: this.headers(),
            body: JSON.stringify(data),
        });
        return res.json();
    },

    async updateProduct(id, data) {
        const res = await fetch(`/api/products/${id}/update/`, {
            method: 'POST',
            headers: this.headers(),
            body: JSON.stringify(data),
        });
        return res.json();
    },

    async deleteProduct(id) {
        const res = await fetch(`/api/products/${id}/delete/`, {
            method: 'POST',
            headers: this.headers(),
        });
        return res.json();
    },

    async searchCatalog(q) {
        const res = await fetch(`/api/catalog-lookup/?q=${encodeURIComponent(q)}`);
        return res.json();
    },

    // Supplies
    async getSupplies(params = {}) {
        const query = new URLSearchParams(params).toString();
        const res = await fetch(`/api/supplies/?${query}`);
        return res.json();
    },

    async createSupply(data) {
        const res = await fetch('/api/supplies/create/', {
            method: 'POST',
            headers: this.headers(),
            body: JSON.stringify(data),
        });
        return res.json();
    },

    async searchStockSerials(q) {
        const res = await fetch(`/api/stock-serials/?q=${encodeURIComponent(q)}`);
        return res.json();
    },

    // Sales
    async getSales(params = {}) {
        const query = new URLSearchParams(params).toString();
        const res = await fetch(`/api/sales/?${query}`);
        return res.json();
    },

    async createSale(data) {
        const res = await fetch('/api/sales/create/', {
            method: 'POST',
            headers: this.headers(),
            body: JSON.stringify(data),
        });
        return res.json();
    },

    // Helpers
    headers() {
        const csrf = this.getCookie('csrftoken');
        return {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf,
        };
    },

    getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return '';
    },
};

// ============ UI Helpers ============

function showAlert(message, type = 'error') {
    const existing = document.querySelector('.alert');
    if (existing) existing.remove();

    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    document.querySelector('.content')?.prepend(alert);

    setTimeout(() => alert.remove(), 5000);
}

function formatPrice(price) {
    return new Intl.NumberFormat('ru-RU').format(price) + ' ₽';
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    return dateStr;
}

function getStatusBadge(status) {
    const badges = {
        'instock': '<span class="badge badge-success">В наличии</span>',
        'low': '<span class="badge badge-warning">Мало</span>',
        'out': '<span class="badge badge-danger">Нет</span>',
        'received': '<span class="badge badge-success">Получено</span>',
        'pending': '<span class="badge badge-warning">Ожидается</span>',
        'sold': '<span class="badge badge-info">Продано</span>',
        'completed': '<span class="badge badge-success">Завершена</span>',
    };
    return badges[status] || `<span class="badge">${status}</span>`;
}

// ============ Pagination ============

function renderPagination(container, page, pages, callback) {
    if (pages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = '<div class="pagination">';

    if (page > 1) {
        html += `<button class="btn btn-sm" onclick="${callback}(${page - 1})">← Назад</button>`;
    }

    for (let i = 1; i <= pages; i++) {
        if (i === page) {
            html += `<span class="btn btn-sm btn-primary">${i}</span>`;
        } else if (i <= 3 || i > pages - 3 || Math.abs(i - page) <= 1) {
            html += `<button class="btn btn-sm" onclick="${callback}(${i})">${i}</button>`;
        } else if (i === 4 || i === pages - 3) {
            html += '<span class="btn btn-sm">...</span>';
        }
    }

    if (page < pages) {
        html += `<button class="btn btn-sm" onclick="${callback}(${page + 1})">Вперёд →</button>`;
    }

    html += '</div>';
    container.innerHTML = html;
}
