// SmartWardrobe API 层
// ============================================================
// 注意：所有敏感操作（refreshToken）包含防循环保护。
// 图片路径日志仅在 debug 模式下输出。

const API_BASE_URL = (typeof window !== 'undefined' && window.API_BASE_URL) || 'http://127.0.0.1:8000';

const TOKEN_KEY = 'smart_wardrobe_access_token';
const REFRESH_TOKEN_KEY = 'smart_wardrobe_refresh_token';

// ── Token 管理 ──

function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

function saveToken(accessToken, refreshToken) {
    localStorage.setItem(TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
}

function getRefreshToken() {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
}

// ── 刷新 Token 防循环 ──

let isRefreshing = false;
let refreshQueue = [];

async function refreshAccessToken() {
    if (isRefreshing) {
        // 已在刷新中，排队等待
        return new Promise((resolve, reject) => {
            refreshQueue.push({ resolve, reject });
        });
    }

    isRefreshing = true;
    try {
        const refreshTk = getRefreshToken();
        if (!refreshTk) throw new Error('No refresh token');

        const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${refreshTk}`,
            },
        });

        if (!response.ok) throw new Error('Refresh failed');

        const data = await response.json();
        saveToken(data.access_token, data.refresh_token);

        // 处理等待队列
        refreshQueue.forEach(p => p.resolve(data.access_token));
        refreshQueue = [];
        return data.access_token;
    } catch (e) {
        refreshQueue.forEach(p => p.reject(e));
        refreshQueue = [];
        clearToken();
        throw e;
    } finally {
        isRefreshing = false;
    }
}

// ── 通用请求 ──

async function request(url, options = {}) {
    const token = getToken();
    const headers = { ...(options.headers || {}) };

    // 非 FormData 自动设置 Content-Type
    if (!(options.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
    }

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    // 生产环境不输出调试日志
    if (window.__DEV__) {
        console.log(`[API] ${options.method || 'GET'} ${url}`);
    }

    try {
        const response = await fetch(`${API_BASE_URL}${url}`, { ...options, headers });

        // 401 → 尝试刷新 Token（最多重试 1 次）
        if (response.status === 401 && getRefreshToken()) {
            try {
                const newToken = await refreshAccessToken();
                headers['Authorization'] = `Bearer ${newToken}`;
                const retryResponse = await fetch(`${API_BASE_URL}${url}`, { ...options, headers });
                return handleResponse(retryResponse);
            } catch {
                clearToken();
                throw new Error('登录已过期，请重新登录');
            }
        }

        return handleResponse(response);
    } catch (error) {
        console.error('[API Error]', error);
        throw error;
    }
}

async function handleResponse(response) {
    let data;
    try {
        const text = await response.text();
        data = text ? JSON.parse(text) : {};
    } catch {
        data = {};
    }

    if (!response.ok) {
        throw new Error(data.detail || data.message || `请求失败 (${response.status})`);
    }
    return data;
}

// ── API 模块 ──

const api = {
    getToken,
    saveToken,
    clearToken,

    authAPI: {
        register: (userData) =>
            request('/auth/register', { method: 'POST', body: JSON.stringify(userData) }),
        login: (loginData) =>
            request('/auth/login', { method: 'POST', body: JSON.stringify(loginData) }),
        logout: () =>
            request('/auth/logout', { method: 'POST' }),
    },

    wardrobeAPI: {
        getGarments: (params = {}) => {
            const qs = new URLSearchParams(params).toString();
            return request(`/wardrobe/items${qs ? '?' + qs : ''}`);
        },
        createGarment: (formData) =>
            request('/wardrobe/items', { method: 'POST', body: formData, headers: {} }),
        updateGarment: (id, data) =>
            request(`/wardrobe/items/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
        deleteGarment: (id) =>
            request(`/wardrobe/items/${id}`, { method: 'DELETE' }),
    },

    tryonAPI: {
        generateTryon: (formData) =>
            request('/tryon/generate', { method: 'POST', body: formData, headers: {} }),
        getTryonRecord: (id) =>
            request(`/tryon/records/${id}`),
    },

    recommendationAPI: {
        getDailyRecommendations: (params) =>
            request('/recommendations/daily', { method: 'POST', body: JSON.stringify(params) }),
        getAutoRecommendations: (city = '北京') =>
            request(`/recommendations/auto?city=${encodeURIComponent(city)}`),
    },

    recordsAPI: {
        getTryonHistory: (params = {}) => {
            const qs = new URLSearchParams(params).toString();
            return request(`/records/history${qs ? '?' + qs : ''}`);
        },
        getRecommendationHistory: (params = {}) => {
            const qs = new URLSearchParams(params).toString();
            return request(`/records/recommendations${qs ? '?' + qs : ''}`);
        },
        getFavorites: (params = {}) => {
            const qs = new URLSearchParams(params).toString();
            return request(`/records/favorites${qs ? '?' + qs : ''}`);
        },
        addFavorite: (tryonRecordId) =>
            request('/records/favorites', { method: 'POST', body: JSON.stringify({ tryon_record_id: tryonRecordId }) }),
        deleteFavorite: (id) =>
            request(`/records/favorites/${id}`, { method: 'DELETE' }),
    },

    profileAPI: {
        getProfile: () => request('/profile/me'),
        updateProfile: (data) =>
            request('/profile/me', { method: 'PUT', body: JSON.stringify(data) }),
        updateAvatar: (formData) =>
            request('/profile/avatar', { method: 'POST', body: formData, headers: {} }),
        updatePassword: (data) =>
            request('/profile/password', { method: 'PUT', body: JSON.stringify(data) }),
    },

    // 天气：调用后端真实接口（后端会回退到模拟数据）
    weatherAPI: {
        getWeather: async (city) => {
            // 后端 weather 接口已存在，在 /weather?city=xxx
            return request(`/weather?city=${encodeURIComponent(city || '北京')}`);
        },
    },
};

window.api = api;
window.API_BASE_URL = API_BASE_URL;
