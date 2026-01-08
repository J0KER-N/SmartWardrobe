# 前后端衔接问题分析报告

## 🔴 严重问题

### 1. 前端未引入 API 文件
**问题**: `index.html` 中没有引入 `api.js` 文件
**位置**: `front/index.html`
**影响**: 前端无法调用后端 API，所有功能都是模拟的

**修复**: 在 `index.html` 的 `<head>` 或 `</body>` 前添加：
```html
<script src="api.js"></script>
```

---

### 2. 前端未实际调用后端 API
**问题**: 登录、注册等功能都是模拟的，没有真正调用后端
**位置**: `front/index.html` 中的 `login()` 和 `register()` 方法

**当前代码**:
```javascript
login() {
  // 只是验证输入，然后直接跳转
  this.showPage('homePage');
}

register() {
  // 只是验证输入，显示成功提示
  vant.Toast.success('注册成功');
  this.showPage('loginPage');
}
```

**应该改为**:
```javascript
async login() {
  if (!this.phone) {
    vant.Toast('请输入手机号码');
    return;
  }
  if (this.isPwdLogin && !this.password) {
    vant.Toast('请输入密码');
    return;
  }
  if (!this.isPwdLogin && !this.code) {
    vant.Toast('请输入验证码');
    return;
  }
  
  try {
    vant.Toast.loading({ message: '登录中...', duration: 0 });
    const response = await window.api.authAPI.login({
      phone: this.phone,
      password: this.password
    });
    
    // 保存token
    window.api.saveToken(response.access_token, response.refresh_token);
    
    // 获取用户信息
    const userInfo = await window.api.profileAPI.getProfile();
    this.nickname = userInfo.nickname;
    this.userAvatar = userInfo.avatar_url || 'https://picsum.photos/seed/avatar/100/100';
    
    vant.Toast.clear();
    vant.Toast.success('登录成功');
    this.showPage('homePage');
  } catch (error) {
    vant.Toast.clear();
    vant.Toast.fail(error.message || '登录失败');
  }
}
```

---

### 3. API 路径不匹配

#### 问题 3.1: 更新个人信息路径错误
- **前端**: `/profile/update` (PUT)
- **后端**: `/profile/me` (PUT)
- **修复**: 修改 `front/api.js` 第 247 行

#### 问题 3.2: 保存试穿记录路径不存在
- **前端**: `/records/save/{id}` (POST)
- **后端**: 没有这个路由
- **修复**: 删除或修改前端调用，或添加后端路由

---

### 4. 衣物数据未从后端加载
**问题**: 衣物列表是硬编码的，没有从后端获取
**位置**: `front/index.html` 中的 `clothesList` 数据

**当前代码**:
```javascript
clothesList: [
  { id: 1, name: '短袖', ... },  // 硬编码数据
  { id: 2, name: '短袖', ... },
  ...
]
```

**应该改为**:
```javascript
async mounted() {
  // ... 现有代码 ...
  
  // 加载衣物列表
  await this.loadGarments();
}

async loadGarments() {
  try {
    const garments = await window.api.wardrobeAPI.getGarments();
    this.clothesList = garments.map(g => ({
      id: g.id,
      name: g.name,
      desc: g.tags.join(' · ') || g.category,
      category: g.category,
      price: 0, // 后端没有价格字段
      imgUrl: `${API_BASE_URL}${g.image_url}`, // 需要拼接完整URL
      season: g.season ? [g.season] : [],
      color: g.color || ''
    }));
    this.filteredClothes = [...this.clothesList];
  } catch (error) {
    console.error('加载衣物失败:', error);
    // 如果未登录，使用空列表
    this.clothesList = [];
    this.filteredClothes = [];
  }
}
```

---

### 5. 添加衣物未调用后端 API
**问题**: `saveToWardrobe()` 方法只是添加到本地数组，没有保存到后端
**位置**: `front/index.html` 中的 `saveToWardrobe()` 方法

**应该改为**:
```javascript
async saveToWardrobe() {
  // 验证表单
  if (!this.newClothesImg) {
    vant.Toast('请选择衣物图片');
    return;
  }
  
  if (!this.newClothesName) {
    vant.Toast('请输入服装名称');
    return;
  }
  
  if (!this.newClothesCategory) {
    vant.Toast('请选择分类');
    return;
  }
  
  try {
    vant.Toast.loading({ message: '保存中...', duration: 0 });
    
    // 创建FormData
    const formData = new FormData();
    // 需要将base64图片转换为File对象，或直接使用File对象
    // 这里假设newClothesImg是File对象或base64
    if (this.newClothesImgFile) {
      formData.append('file', this.newClothesImgFile);
    }
    formData.append('name', this.newClothesName);
    formData.append('category', this.newClothesCategory);
    if (this.newClothesSeason) {
      formData.append('season', this.newClothesSeason);
    }
    if (this.newClothesColor) {
      formData.append('color', this.newClothesColor);
    }
    
    // 调用后端API
    const garment = await window.api.wardrobeAPI.createGarment(formData);
    
    vant.Toast.clear();
    vant.Toast.success('成功添加到衣橱');
    
    // 重新加载衣物列表
    await this.loadGarments();
    
    // 重置表单
    this.resetClothesForm();
    
    // 返回衣橱页面
    this.goBackToPrevious();
  } catch (error) {
    vant.Toast.clear();
    vant.Toast.fail(error.message || '保存失败');
  }
}
```

---

### 6. 图片 URL 需要完整路径
**问题**: 后端返回的图片路径是相对路径（如 `/uploads/garments/...`），前端需要拼接完整URL
**修复**: 在显示图片时拼接 `API_BASE_URL`

```javascript
// 在loadGarments中
imgUrl: `${API_BASE_URL}${g.image_url}`

// 或者创建一个辅助方法
getImageUrl(path) {
  if (!path) return 'https://picsum.photos/seed/default/200/120';
  if (path.startsWith('http')) return path;
  return `${API_BASE_URL}${path}`;
}
```

---

### 7. 缺少错误处理和加载状态
**问题**: 大部分API调用缺少错误处理和加载提示
**建议**: 统一添加 try-catch 和加载提示

---

### 8. Token 管理问题
**问题**: 前端没有在页面加载时检查token，也没有在token过期时自动跳转登录
**修复**: 在 `mounted()` 中检查token，如果存在则自动获取用户信息

```javascript
async mounted() {
  // ... 现有代码 ...
  
  // 检查是否已登录
  const token = window.api.getToken();
  if (token) {
    try {
      const userInfo = await window.api.profileAPI.getProfile();
      this.nickname = userInfo.nickname;
      this.userAvatar = userInfo.avatar_url || 'https://picsum.photos/seed/avatar/100/100';
      // 加载衣物列表
      await this.loadGarments();
    } catch (error) {
      // Token无效，清除并跳转登录
      window.api.clearToken();
      this.showPage('loginPage');
    }
  }
}
```

---

## 📋 修复优先级

### P0 - 必须立即修复
1. ✅ 引入 `api.js` 文件
2. ✅ 修复登录/注册调用后端API
3. ✅ 修复API路径不匹配问题

### P1 - 高优先级
4. ✅ 从后端加载衣物数据
5. ✅ 添加衣物时调用后端API
6. ✅ 修复图片URL拼接

### P2 - 中优先级
7. ✅ 添加错误处理和加载状态
8. ✅ 完善Token管理

---

## 🔧 快速修复步骤

1. **在 `index.html` 中引入 `api.js`**:
```html
<script src="api.js"></script>
```

2. **修复 `api.js` 中的路径**:
```javascript
// 修改 profileAPI.updateProfile
updateProfile: async (profileData) => {
    return request('/profile/me', {  // 改为 /profile/me
        method: 'PUT',
        body: JSON.stringify(profileData),
    });
},
```

3. **修改登录方法调用后端API**（见上面代码示例）

4. **修改注册方法调用后端API**（类似登录）

5. **添加加载衣物数据的方法**（见上面代码示例）

6. **修改添加衣物方法调用后端API**（见上面代码示例）

---

## 📝 注意事项

1. **CORS配置**: 确保后端的 `FRONTEND_ORIGIN` 配置包含前端地址
2. **API_BASE_URL**: 确保 `api.js` 中的 `API_BASE_URL` 指向正确的后端地址
3. **文件上传**: 添加衣物时的图片上传需要使用 `FormData`，确保正确处理
4. **错误处理**: 所有API调用都应该有错误处理，给用户友好的提示




