/**
 * API 服务封装
 * 所有后端接口调用统一管理
 */

const API_BASE_URL = 'http://127.0.0.1:8000'; // 后端 API 地址

// 获取 token
function getToken() {
  return localStorage.getItem('access_token');
}

// 获取刷新 token
function getRefreshToken() {
  return localStorage.getItem('refresh_token');
}

// 保存 token
function saveToken(accessToken, refreshToken) {
  localStorage.setItem('access_token', accessToken);
  if (refreshToken) {
    localStorage.setItem('refresh_token', refreshToken);
  }
}

// 清除 token
function clearToken() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

// 通用请求函数
async function request(url, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(`${API_BASE_URL}${url}`, {
      ...options,
      headers,
    });

    // 处理 401 未授权，尝试刷新 token
    if (response.status === 401 && getRefreshToken()) {
      try {
        const refreshResponse = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: getRefreshToken() }),
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
          return await retryResponse.json();
        } else {
          clearToken();
          throw new Error('登录已过期，请重新登录');
        }
      } catch (error) {
        clearToken();
        throw error;
      }
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || '请求失败');
    }

    return await response.json();
  } catch (error) {
    console.error('API Request Error:', error);
    throw error;
  }
}

// 文件上传请求
async function uploadFile(url, formData) {
  const token = getToken();
  const headers = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${url}`, {
    method: 'POST',
    headers,
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || '上传失败');
  }

  return await response.json();
}

// ==================== 认证相关 API ====================

export const authAPI = {
  // 注册
  register: async (phone, password, nickname) => {
    return request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ phone, password, nickname }),
    });
  },

  // 登录
  login: async (phone, password) => {
    const formData = new FormData();
    formData.append('username', phone);
    formData.append('password', password);

    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || '登录失败');
    }

    const data = await response.json();
    saveToken(data.access_token, data.refresh_token);
    return data;
  },

  // 刷新 token
  refreshToken: async () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      throw new Error('没有刷新令牌');
    }

    const data = await request('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    saveToken(data.access_token, data.refresh_token);
    return data;
  },

  // 退出登录
  logout: () => {
    clearToken();
  },
};

// ==================== 用户相关 API ====================

export const userAPI = {
  // 获取当前用户信息
  getCurrentUser: async () => {
    return request('/profile/me');
  },

  // 更新用户信息
  updateUser: async (data) => {
    return request('/profile/update', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  // 更新密码
  updatePassword: async (oldPassword, newPassword) => {
    return request('/profile/password', {
      method: 'PUT',
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
    });
  },
};

// ==================== 衣橱相关 API ====================

export const wardrobeAPI = {
  // 获取衣物列表
  getGarments: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return request(`/wardrobe/items${queryString ? '?' + queryString : ''}`);
  },

  // 创建衣物
  createGarment: async (formData) => {
    return uploadFile('/wardrobe/items', formData);
  },

  // 更新衣物
  updateGarment: async (garmentId, data) => {
    return request(`/wardrobe/items/${garmentId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  // 删除衣物
  deleteGarment: async (garmentId) => {
    return request(`/wardrobe/items/${garmentId}`, {
      method: 'DELETE',
    });
  },
};

// ==================== 试穿相关 API ====================

export const tryonAPI = {
  // 生成试穿效果
  generateTryon: async (garmentIds, userPhoto, prompt) => {
    const formData = new FormData();
    formData.append('user_photo', userPhoto);
    formData.append('garment_ids', JSON.stringify(garmentIds));
    if (prompt) {
      formData.append('prompt', prompt);
    }

    return uploadFile('/tryon/generate', formData);
  },
};

// ==================== 推荐相关 API ====================

export const recommendationAPI = {
  // 获取每日推荐
  getDailyRecommendation: async (city) => {
    return request('/recommendations/daily', {
      method: 'POST',
      body: JSON.stringify({ city }),
    });
  },
};

// ==================== 记录相关 API ====================

export const recordsAPI = {
  // 获取试穿历史
  getHistory: async (page = 1, pageSize = 20) => {
    return request(`/records/history?page=${page}&page_size=${pageSize}`);
  },

  // 获取历史记录总数
  getHistoryCount: async () => {
    return request('/records/history/count');
  },

  // 添加收藏
  addFavorite: async (recordId, notes) => {
    return request('/records/favorites', {
      method: 'POST',
      body: JSON.stringify({ record_id: recordId, notes }),
    });
  },

  // 获取收藏列表
  getFavorites: async (page = 1, pageSize = 20) => {
    return request(`/records/favorites?page=${page}&page_size=${pageSize}`);
  },
};

// 导出所有 API
export default {
  auth: authAPI,
  user: userAPI,
  wardrobe: wardrobeAPI,
  tryon: tryonAPI,
  recommendation: recommendationAPI,
  records: recordsAPI,
  getToken,
  clearToken,
};

