// API基础配置
// 在浏览器环境中不能使用 process.env，直接使用默认值
// 如果需要修改，可以直接改这里的值，或者通过 window.API_BASE_URL 覆盖
const API_BASE_URL = (typeof window !== 'undefined' && window.API_BASE_URL) || 'http://127.0.0.1:8000';

// Token管理
const TOKEN_KEY = 'smart_wardrobe_access_token';
const REFRESH_TOKEN_KEY = 'smart_wardrobe_refresh_token';

// 获取Token
function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

// 保存Token
function saveToken(accessToken, refreshToken) {
    localStorage.setItem(TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

// 清除Token
function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
}

// 获取刷新Token
function getRefreshToken() {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
}

// 通用请求函数
async function request(url, options = {}) {
    const token = getToken();
    // 合并 headers；若 body 是 FormData 则不要设置 Content-Type（浏览器会自动设置边界）
    const headers = {
        ...(options.headers || {})
    };
    if (!(options.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
    }

    // 添加认证头
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    try {
        console.log(`[API请求] ${options.method || 'GET'} ${API_BASE_URL}${url}`, {
            headers,
            body: options.body instanceof FormData ? '[FormData]' : options.body
        });
        
        const response = await fetch(`${API_BASE_URL}${url}`, {
            ...options,
            headers,
        });

        console.log(`[API响应] ${response.status} ${response.statusText}`, response);

        // 处理401错误（Token过期）
        if (response.status === 401 && getRefreshToken()) {
            try {
                // 尝试刷新Token
                const refreshResponse = await fetch(`${API_BASE_URL}/auth/refresh`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${getRefreshToken()}`,
                    },
                });

                if (refreshResponse.ok) {
                    const refreshData = await refreshResponse.json();
                    saveToken(refreshData.access_token, refreshData.refresh_token);
                    
                    // 重试原请求
                    headers['Authorization'] = `Bearer ${refreshData.access_token}`;
                    const retryResponse = await fetch(`${API_BASE_URL}${url}`, {
                        ...options,
                        headers,
                    });
                    return handleResponse(retryResponse);
                } else {
                    // 刷新失败，清除Token
                    clearToken();
                    throw new Error('登录已过期，请重新登录');
                }
            } catch (refreshError) {
                clearToken();
                throw refreshError;
            }
        }

        return handleResponse(response);
    } catch (error) {
        console.error('API请求错误:', error);
        throw error;
    }
}

// 响应处理
async function handleResponse(response) {
    let data;
    try {
        const text = await response.text();
        console.log(`[响应内容]`, text);
        data = text ? JSON.parse(text) : {};
    } catch (e) {
        console.error('[响应解析失败]', e);
        data = {};
    }
    
    if (!response.ok) {
        const errorMsg = data.detail || data.message || `请求失败 (${response.status})`;
        console.error(`[API错误] ${response.status}:`, errorMsg, data);
        throw new Error(errorMsg);
    }
    
    return data;
}

// API模块封装
const api = {
    // Token管理
    getToken,
    saveToken,
    clearToken,
    
    // 认证相关
    authAPI: {
        // 注册
        register: async (userData) => {
            return request('/auth/register', {
                method: 'POST',
                body: JSON.stringify(userData),
            });
        },
        // 登录
        login: async (loginData) => {
            return request('/auth/login', {
                method: 'POST',
                body: JSON.stringify(loginData),
            });
        },
        // 刷新Token
        refreshToken: async () => {
            return request('/auth/refresh', {
                method: 'POST',
                body: JSON.stringify({ refresh_token: getRefreshToken() }),
            });
        },
        // 登出
        logout: async () => {
            return request('/auth/logout', {
                method: 'POST',
            });
        },
    },
    
    // 衣橱管理
    wardrobeAPI: {
        // 获取衣物列表
        getGarments: async (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return request(`/wardrobe/items${queryString ? '?' + queryString : ''}`);
        },
        // 创建衣物
        createGarment: async (formData) => {
            return request('/wardrobe/items', {
                method: 'POST',
                body: formData,
                headers: {}, // 让浏览器自动设置Content-Type
            });
        },
        // 更新衣物
        updateGarment: async (id, garmentData) => {
            return request(`/wardrobe/items/${id}`, {
                method: 'PUT',
                body: JSON.stringify(garmentData),
            });
        },
        // 删除衣物
        deleteGarment: async (id) => {
            return request(`/wardrobe/items/${id}`, {
                method: 'DELETE',
            });
        },
    },
    
    // 虚拟试穿
    tryonAPI: {
        // 生成试穿效果
        generateTryon: async (formData) => {
            return request('/tryon/generate', {
                method: 'POST',
                body: formData,
                headers: {},
            });
        },
        // 获取试穿记录
        getTryonRecord: async (id) => {
            return request(`/tryon/records/${id}`);
        },
    },
    
    // 穿搭推荐
    recommendationAPI: {
        // 每日推荐
        getDailyRecommendations: async (params) => {
            return request('/recommendations/daily', {
                method: 'POST',
                body: JSON.stringify(params),
            });
        },
    },
    
    // 记录管理
    recordsAPI: {
        // 获取试穿历史
        getTryonHistory: async (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return request(`/records/history${queryString ? '?' + queryString : ''}`);
        },
        // 获取收藏列表
        getFavorites: async (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return request(`/records/favorites${queryString ? '?' + queryString : ''}`);
        },
        // 添加收藏
        addFavorite: async (tryonRecordId) => {
            return request('/records/favorites', {
                method: 'POST',
                body: JSON.stringify({ tryon_record_id: tryonRecordId }),
            });
        },
        // 删除收藏
        deleteFavorite: async (id) => {
            return request(`/records/favorites/${id}`, {
                method: 'DELETE',
            });
        },
        // 删除试穿记录
        deleteTryonRecord: async (id) => {
            return request(`/records/history/${id}`, {
                method: 'DELETE',
            });
        },
        // 保存试穿记录
        saveTryonRecord: async (id) => {
            return request(`/records/save/${id}`, {
                method: 'POST',
            });
        },
    },
    
    // 个人中心
    profileAPI: {
        // 获取个人信息
        getProfile: async () => {
            return request('/profile/me');
        },
        // 更新个人信息
        updateProfile: async (profileData) => {
            return request('/profile/me', {
                method: 'PUT',
                body: JSON.stringify(profileData),
            });
        },
        // 更新头像
        updateAvatar: async (formData) => {
            return request('/profile/avatar', {
                method: 'POST',
                body: formData,
                headers: {},
            });
        },
        // 修改密码
        updatePassword: async (passwordData) => {
            return request('/profile/password', {
                method: 'PUT',
                body: JSON.stringify(passwordData),
            });
        },
    },
    
    // 天气服务
    weatherAPI: {
        // 获取天气
        getWeather: async (city) => {
            // 模拟天气数据，实际项目中调用后端接口
            return new Promise(resolve => {
                setTimeout(() => {
                    resolve({
                        city: city,
                        condition: '晴',
                        temp_c: 25,
                        humidity: 60,
                    });
                }, 500);
            });
            // 实际接口调用：
            // return request(`/weather?city=${encodeURIComponent(city)}`);
        },
    },
};

// 暴露API对象和配置
window.api = api;
// 暴露API_BASE_URL供外部使用
if (typeof window !== 'undefined') {
    window.API_BASE_URL = API_BASE_URL;
}