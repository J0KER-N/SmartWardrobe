import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..dependencies import get_db, get_current_user
from ..services.engagement_metrics import build_analytics_overview

router = APIRouter(prefix="/admin", tags=["admin"])


def _escape_html(value):
    text = "" if value is None else str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _format_number(value):
    if value is None:
        return "-"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _is_dev_admin(user) -> bool:
    dev_admins = [s.strip() for s in os.getenv("DEV_ADMINS", "").split(",") if s.strip()]
    identifiers = [
        getattr(user, "username", None),
        getattr(user, "email", None),
        getattr(user, "phone", None),
        getattr(user, "nickname", None),
    ]
    return bool(getattr(user, "is_admin", False) or any(identifier in dev_admins for identifier in identifiers if identifier))


@router.get("/ui", response_class=HTMLResponse)
def admin_ui(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """受保护的开发者后台 UI。"""
    if not _is_dev_admin(user):
        raise HTTPException(status_code=403, detail="未授权访问")

    data = build_analytics_overview(db)
    gm = data.get("garment_metrics", {}) or {}
    um = data.get("user_metrics", {}) or {}
    fitm = data.get("fit_feedback_metrics", {}) or {}

    garments = gm.get("top_tryon_garments", [])
    top_favorites = gm.get("top_favorite_garments", [])
    style_heat = gm.get("style_heat", [])
    body_shape_distribution = um.get("body_shape_distribution", []) or []
    fit_source_distribution = fitm.get("fit_source_distribution", []) or []
    fit_status_distribution = fitm.get("fit_status_distribution", []) or []
    online_fit_status_distribution = fitm.get("online_fit_status_distribution", []) or []
    offline_fit_status_distribution = fitm.get("offline_fit_status_distribution", []) or []
    online_top_fit_garments = fitm.get("online_top_fit_garments", []) or []
    offline_top_fit_garments = fitm.get("offline_top_fit_garments", []) or []
    garment_size_distribution = fitm.get("garment_size_distribution", []) or []
    online_garment_size_distribution = fitm.get("online_garment_size_distribution", []) or []
    offline_garment_size_distribution = fitm.get("offline_garment_size_distribution", []) or []
    online_body_shape_distribution = fitm.get("online_body_shape_distribution", []) or []
    offline_body_shape_distribution = fitm.get("offline_body_shape_distribution", []) or []
    top_fit_garments = fitm.get("top_fit_garments", [])
    offline_binding_count = int(fitm.get("offline_binding_count", 0) or 0)
    online_fit_feedback_count = int(fitm.get("online_fit_feedback_count", 0) or 0)
    offline_fit_feedback_count = int(fitm.get("offline_fit_feedback_count", 0) or 0)

    total_users = int(um.get("total_users", 0) or 0)
    profiled_users = int(um.get("profiled_users", 0) or 0)
    average_height = um.get("average_height_cm")
    average_weight = um.get("average_weight_kg")
    total_garments = int(gm.get("total_garments", 0) or 0)
    total_tryon_records = int(gm.get("total_tryon_records", 0) or 0)
    total_feedback = int(fitm.get("total_feedback", 0) or 0)
    fit_feedback_count = int(fitm.get("fit_feedback_count", 0) or 0)
    avg_fit_rate = round((fit_feedback_count / total_feedback) * 100, 1) if total_feedback else 0

    top_tryon_sum = sum(int(item.get("tryon_count", 0) or 0) for item in garments)
    top_favorite_sum = sum(int(item.get("favorite_count", 0) or 0) for item in top_favorites)

    # 使用提供的 React JSX 模板的静态等价 HTML/CSS（保持服务器渲染与数据插槽）
    html = [
        "<!doctype html>",
        "<html lang='zh-CN'>",
        "<head>",
        "<meta charset='utf-8' />",
        "<meta name='viewport' content='width=device-width, initial-scale=1' />",
        "<title>开发者后台 - 分析概览</title>",
        "<style>",
        ":root{--bg:#f1f5f9;--panel:#ffffff;--text:#0f172a;--muted:#64748b;--line:#e2e8f0}",
        "*{box-sizing:border-box}body{margin:0;min-height:100vh;font-family:Inter,Segoe UI,Arial,sans-serif;background:linear-gradient(180deg,#f8fafc 0,#eef2ff 100%);color:var(--text)}",
        ".wrap{max-width:1200px;margin:0 auto;padding:24px}.rounded-2xl{border-radius:18px}.card{background:var(--panel);border:1px solid var(--line);padding:18px}.grid{display:grid;gap:14px}.flex{display:flex}.items-center{align-items:center}.justify-between{justify-content:space-between}.text-slate-500{color:#64748b}.text-slate-950{color:#0f172a}.bg-white{background:#fff}.shadow-sm{box-shadow:0 6px 18px rgba(15,23,42,.06)}",
        "table{width:100%;border-collapse:collapse}.p-3{padding:12px}.text-center{text-align:center}.font-medium{font-weight:600}",
        "@media (min-width:1000px){.cols-4{grid-template-columns:repeat(4,1fr)}.cols-3{grid-template-columns:repeat(3,1fr)}.cols-2{grid-template-columns:repeat(2,1fr)}}",
        "</style>",
        "</head>",
        "<body>",
        "<div class='wrap'>",
        "<div class='flex' style='gap:18px;align-items:stretch'>",
        "<div style='flex:1 1 65%'>",
        "<div class='card rounded-2xl'>",
        "<div class='eyebrow' style='display:inline-flex;gap:8px;padding:8px 12px;border-radius:999px;background:rgba(20,184,166,.10);border:1px solid rgba(20,184,166,.18);color:#0f766e;font-size:12px;font-weight:700'>VisionFit 体型数据资产看板</div>",
        "<h1 style='margin:16px 0 10px;font-size:28px'>从镜子采集到版型决策</h1>",
        "<p class='text-slate-500'>基于线上试穿、线下镜子采集与尺码绑定反馈，输出款式热度、体型分层、合身度分布和备货建议。</p>",
        "</div>",
        "</div>",
        "<div style='flex:1 1 35%'>",
        "<div class='card rounded-2xl'>",
        f"<div class='mini'><div class='k'>总用户数</div><div class='v'>{_format_number(total_users)}</div><div class='s text-slate-500'>已填写体型：{_format_number(profiled_users)}</div></div>",
        f"<div class='mini' style='margin-top:12px'><div class='k'>总试穿记录</div><div class='v'>{_format_number(total_tryon_records)}</div><div class='s text-slate-500'>衣物总数：{_format_number(total_garments)}</div></div>",
        "</div>",
        "</div>",
        "</div>",
        "<div style='margin-top:18px' class='grid cols-4'>",
        f"<div class='card rounded-2xl'><div class='kpi'>Top 试穿总量</div><div class='value'>{_format_number(top_tryon_sum)}</div></div>",
        f"<div class='card rounded-2xl'><div class='kpi'>Top 收藏总量</div><div class='value'>{_format_number(top_favorite_sum)}</div></div>",
        f"<div class='card rounded-2xl'><div class='kpi'>试穿反馈总数</div><div class='value'>{_format_number(total_feedback)}</div></div>",
        f"<div class='card rounded-2xl'><div class='kpi'>已绑定反馈</div><div class='value'>{_format_number(fit_feedback_count)}</div></div>",
        "</div>",
        "<div style='margin-top:18px' class='grid cols-2' >",
        "<div class='card rounded-2xl'>",
        "<h2 style='font-size:18px;margin:0'>匿名体型数据库：身高 × 体重分布</h2>",
        "<p class='text-slate-500' style='margin-top:6px'>用于识别门店真实客群体型结构</p>",
        "<div style='height:320px;background:linear-gradient(180deg,#f8fafc,#fff);display:flex;align-items:center;justify-content:center;margin-top:12px'>",
        "<div class='text-slate-500'>可视化 (前端图表) — 请在前端集成 `body_scatter` 数据</div>",
        "</div>",
        "</div>",
        "<div class='card rounded-2xl'>",
        "<h2 style='font-size:18px;margin:0'>体型档案增长与有效率</h2>",
        "<p class='text-slate-500' style='margin-top:6px'>设备铺设后可持续沉淀本地客群数据</p>",
        "<div style='height:320px;display:flex;align-items:center;justify-content:center;margin-top:12px'>",
        "<div class='text-slate-500'>区域趋势图 (body_profile_trend)</div>",
        "</div>",
        "</div>",
        "</div>",
        "<div style='margin-top:18px' class='card rounded-2xl'>",
        "<h2 style='font-size:18px;margin:0'>尺码需求 vs 当前库存</h2>",
        "<p class='text-slate-500' style='margin-top:6px'>根据进店体型推算真实尺码需求，发现备货偏差</p>",
        "<div style='height:220px;display:flex;align-items:center;justify-content:center;margin-top:12px'>图表占位</div>",
        "</div>",
        "<div style='margin-top:18px' class='card rounded-2xl'>",
        "<h2 style='font-size:18px;margin:0'>部位级合身度热力诊断</h2>",
        "<p class='text-slate-500' style='margin-top:6px'>部位级合身度分解</p>",
        "<div style='margin-top:12px;overflow:auto'>",
    ]

    if garments:
        max_tryon = max(int(item.get("tryon_count", 0) or 0) for item in garments) or 1
        for item in garments:
            name = _escape_html(item.get("name") or f"#{item.get('garment_id') or item.get('id')}")
            category = _escape_html(item.get("category") or "未分类")
            tryon_count = int(item.get("tryon_count", 0) or 0)
            favorite_count = int(item.get("favorite_count", 0) or 0)
            pct = max(4, round((tryon_count / max_tryon) * 100))
            html.extend([
                "<div class='list-item'>",
                f"<div class='item-left'><div class='item-name'>{name}</div><div class='item-sub'>{category} · 收藏 {favorite_count} 次</div></div>",
                f"<div class='pill'>{tryon_count} 次试穿</div>",
                "</div>",
                f"<div class='bar-row'><div class='bar-label'>{name}</div><div class='bar-track'><div class='bar-fill' style='width:{pct}%'></div></div><div class='bar-value'>{tryon_count}</div></div>",
            ])
    else:
        html.append("<div class='empty'>暂无试穿数据</div>")

    # Top 收藏 / Style Heat 区块（template chip-cloud）
    html.extend([
        "</div>",
        "<div class='card rounded-2xl' style='margin-top:18px'>",
        "<h2 style='font-size:18px;margin:0'>Top 收藏 / Style Heat</h2>",
        "<p class='text-slate-500' style='margin-top:6px'>聚合看款式受欢迎程度和热度标签</p>",
        "<div style='display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px'>",
        "<div>",
        f"<div style='padding:12px 0;color:#64748b'>总用户数 <span style='float:right;font-weight:700'>{_format_number(total_users)}</span></div>",
        f"<div style='padding:12px 0;color:#64748b'>已填写体型 <span style='float:right;font-weight:700'>{_format_number(profiled_users)}</span></div>",
        f"<div style='padding:12px 0;color:#64748b'>平均身高 <span style='float:right;font-weight:700'>{_format_number(average_height)} cm</span></div>",
        f"<div style='padding:12px 0;color:#64748b'>平均体重 <span style='float:right;font-weight:700'>{_format_number(average_weight)} kg</span></div>",
        "</div>",
        "<div>",
    ])

    if top_favorites:
        max_fav = max(int(item.get("favorite_count", 0) or 0) for item in top_favorites) or 1
        for item in top_favorites:
            name = _escape_html(item.get("name") or f"#{item.get('garment_id') or item.get('id')}")
            favorite_count = int(item.get("favorite_count", 0) or 0)
            tryon_count = int(item.get("tryon_count", 0) or 0)
            pct = max(4, round((favorite_count / max_fav) * 100))
            html.extend([
                f"<div style='padding:12px 0;border-top:1px solid #eef2f6;display:flex;justify-content:space-between;align-items:center'><div><div style='font-weight:700'>{name}</div><div style='color:#64748b;font-size:12px;margin-top:4px'>试穿 {tryon_count} · 收藏 {favorite_count}</div></div><div style='font-weight:700'>{favorite_count}</div></div>",
                f"<div style='height:10px;border-radius:999px;background:#e2e8f0;margin-top:6px;margin-bottom:8px'><div style='height:100%;border-radius:999px;background:linear-gradient(90deg,#f59e0b,#ff8c75);width:{pct}%;'></div></div>",
            ])
    else:
        html.append("<div style='padding:12px;color:#64748b'>暂无收藏数据</div>")

    html.append("</div>")

    # Style Heat chips
    html.append("<div style='margin-top:12px;display:flex;flex-wrap:wrap;gap:10px'>")
    if style_heat:
        for item in style_heat:
            style = _escape_html(item.get("style"))
            score = float(item.get("score", 0) or 0)
            html.append(f"<div style='padding:10px 12px;border-radius:999px;background:rgba(20,184,166,.08);border:1px solid rgba(20,184,166,.14);font-size:13px'>{style}<span style='color:#64748b;margin-left:8px'>{score:.1f}</span></div>")
    else:
        html.append("<div style='color:#64748b;padding:8px'>暂无风格热度数据</div>")
    html.append("</div>")
    html.append("</div>")

    # 合身度反馈区域
    html.extend([
        "</div>",
        "<div style='margin-top:18px' class='grid cols-2'>",
        "<div class='card rounded-2xl'>",
        "<h2 style='font-size:18px;margin:0'>合身度反馈</h2>",
        "<p class='text-slate-500' style='margin-top:6px'>反馈结果分布与关联衣物</p>",
    ])

    if fit_status_distribution:
        max_fit = max(int(item.get("count", 0) or 0) for item in fit_status_distribution) or 1
        for item in fit_status_distribution:
            label = _escape_html(item.get("fit_status") or "未知")
            count = int(item.get("count", 0) or 0)
            pct = max(4, round((count / max_fit) * 100))
            html.append(f"<div style='display:grid;grid-template-columns:110px 1fr 62px;gap:12px;align-items:center;margin-top:8px'><div style='color:#64748b;font-size:12px'>{label}</div><div style='height:10px;border-radius:999px;background:#e2e8f0;overflow:hidden'><div style='height:100%;border-radius:999px;background:linear-gradient(90deg,#ff7f9d,#f4bf75);width:{pct}%'></div></div><div style='text-align:right;font-size:12px;color:#0f172a'>{count}</div></div>")
    else:
        html.append("<div style='color:#64748b;padding:12px'>暂无合身度反馈</div>")

    html.extend([
        "</div>",
        "<div class='card rounded-2xl'>",
        "<h2 style='font-size:18px;margin:0'>用户数据概览</h2>",
        "<p class='text-slate-500' style='margin-top:6px'>体型信息和均值分布</p>",
        f"<div style='padding:12px 0;color:#64748b'>总用户数 <span style='float:right;font-weight:700'>{_format_number(total_users)}</span></div>",
        f"<div style='padding:12px 0;color:#64748b'>已填写体型 <span style='float:right;font-weight:700'>{_format_number(profiled_users)}</span></div>",
        f"<div style='padding:12px 0;color:#64748b'>平均身高 <span style='float:right;font-weight:700'>{_format_number(average_height)} cm</span></div>",
        f"<div style='padding:12px 0;color:#64748b'>平均体重 <span style='float:right;font-weight:700'>{_format_number(average_weight)} kg</span></div>",
        "</div>",
        "</div>",
    ])

    # 线上 / 线下合身反馈分离区域
    html.extend([
        "<div style='margin-top:18px' class='card rounded-2xl'>",
        "<h2 style='font-size:18px;margin:0'>线上 / 线下合身反馈分离</h2>",
        "<p class='text-slate-500' style='margin-top:6px'>镜子采集与线上反馈分开统计，避免混在一起看不清</p>",
        "</div>",
        "<div style='display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px'>",
        "<div class='card rounded-2xl'>",
        f"<h3 style='margin:0'>线上反馈 · 反馈数 {online_fit_feedback_count}</h3>",
    ])

    if online_fit_status_distribution:
        max_online_fit = max(int(item.get("count", 0) or 0) for item in online_fit_status_distribution) or 1
        for item in online_fit_status_distribution:
            label = _escape_html(item.get("fit_status") or "未知")
            count = int(item.get("count", 0) or 0)
            pct = max(4, round((count / max_online_fit) * 100))
            html.append(f"<div style='display:grid;grid-template-columns:110px 1fr 62px;gap:12px;align-items:center;margin-top:8px'><div style='color:#64748b;font-size:12px'>{label}</div><div style='height:10px;border-radius:999px;background:#e2e8f0;overflow:hidden'><div style='height:100%;border-radius:999px;background:linear-gradient(90deg,#7aa7ff,#b587ff);width:{pct}%'></div></div><div style='text-align:right;font-size:12px;color:#0f172a'>{count}</div></div>")
    else:
        html.append("<div style='color:#64748b;padding:12px'>暂无线上反馈</div>")

    html.extend([
        "</div>",
        "<div class='card rounded-2xl'>",
        f"<h3 style='margin:0'>线下镜子反馈 · 反馈数 {offline_fit_feedback_count} · 绑定样本 {offline_binding_count}</h3>",
    ])

    if offline_fit_status_distribution:
        max_offline_fit = max(int(item.get("count", 0) or 0) for item in offline_fit_status_distribution) or 1
        for item in offline_fit_status_distribution:
            label = _escape_html(item.get("fit_status") or "未知")
            count = int(item.get("count", 0) or 0)
            pct = max(4, round((count / max_offline_fit) * 100))
            html.append(f"<div style='display:grid;grid-template-columns:110px 1fr 62px;gap:12px;align-items:center;margin-top:8px'><div style='color:#64748b;font-size:12px'>{label}</div><div style='height:10px;border-radius:999px;background:#e2e8f0;overflow:hidden'><div style='height:100%;border-radius:999px;background:linear-gradient(90deg,#f4bf75,#ff7f9d);width:{pct}%'></div></div><div style='text-align:right;font-size:12px;color:#0f172a'>{count}</div></div>")
    else:
        html.append("<div style='color:#64748b;padding:12px'>暂无线下反馈</div>")

    html.extend([
        "</div>",
        "</div>",
    ])

    html.extend([
        "<div class='footer'>Last refresh: live server render · 访问路径 /admin/ui</div>",
        "</div>",
        "</div>",
        "</div>",
        "</body></html>",
    ])
    return HTMLResponse("\n".join(html))


@router.get("/login", response_class=HTMLResponse)
def admin_login_page():
    """在浏览器中提供一个简易登录表单。"""
    html = """
    <!doctype html>
    <html lang="zh-CN">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Admin Login</title>
            <style>
                :root{--bg:#f1f5f9;--panel:#ffffff;--text:#0f172a;--muted:#64748b;--accent:#0f172a;--line:#e2e8f0}
                *{box-sizing:border-box}body{margin:0;min-height:100vh;font-family:Inter,Segoe UI,Arial,sans-serif;background:linear-gradient(180deg,#f8fafc 0,#eef2ff 100%);color:var(--text);display:grid;place-items:center;padding:18px}
                .card{width:min(760px,100%);padding:28px;border-radius:24px;background:var(--panel);border:1px solid var(--line);box-shadow:0 10px 30px rgba(15,23,42,.06)}
                .eyebrow{display:inline-flex;align-items:center;padding:8px 12px;border-radius:999px;background:rgba(20,184,166,.10);border:1px solid rgba(20,184,166,.18);color:#0f766e;font-size:12px;letter-spacing:.08em;text-transform:uppercase;font-weight:700}
                h1{margin:16px 0 10px;font-size:32px;letter-spacing:-.03em}p{color:var(--muted);line-height:1.75;margin-top:0}.form{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:16px}label{display:grid;gap:8px;font-size:13px;color:var(--muted)}input{width:100%;padding:14px 14px;border-radius:14px;border:1px solid var(--line);background:#f8fafc;color:var(--text);outline:none}button{grid-column:1/-1;padding:14px 16px;border:none;border-radius:14px;background:linear-gradient(90deg,#14b8a6,#7aa7ff);color:#04101c;font-weight:800;font-size:15px;cursor:pointer}button:hover{filter:brightness(1.05)}.hint{margin-top:12px;color:var(--muted);font-size:12px}.error{margin-top:12px;color:#b42318;min-height:18px}.badge{display:inline-flex;gap:8px;margin-top:14px;padding:10px 12px;border-radius:999px;background:rgba(20,184,166,.08);border:1px solid rgba(20,184,166,.14);color:#0f172a;font-size:12px}.code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}
                @media (max-width:720px){.form{grid-template-columns:1fr}h1{font-size:28px}}
            </style>
    </head>
    <body>
      <div class="card">
        <div class="eyebrow">VisionFit Admin Access</div>
        <h1>开发者后台登录</h1>
        <p>输入手机号和密码后，页面会先获取 token，再加载浅色版内部仪表盘。</p>
        <form id="loginForm" class="form">
          <label>手机号<input id="phone" name="phone" value="13900000001" required /></label>
          <label>密码<input id="password" name="password" type="password" value="AdminPass123" required /></label>
          <button type="submit">登录并打开后台</button>
        </form>
        <div class="badge">默认演示账号 <span class="code">13900000001 / AdminPass123</span></div>
        <div id="message" class="error"></div>
        <div class="hint">如果你已经登录过，也可以直接访问 <span class="code">/admin/ui</span>。</div>
      </div>
      <script>
        const form = document.getElementById('loginForm');
        const msg = document.getElementById('message');
        form.addEventListener('submit', async (e) => {
          e.preventDefault();
          msg.textContent = '';
          const phone = document.getElementById('phone').value.trim();
          const password = document.getElementById('password').value;
          try {
            const r = await fetch('/auth/login', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({phone, password})
            });
            if (!r.ok) {
              const err = await r.json().catch(() => ({detail: '登录失败'}));
              msg.textContent = err.detail || ('登录失败: ' + r.status);
              return;
            }
            const data = await r.json();
            const token = data.access_token;
            if (!token) {
              msg.textContent = '未获取到 token';
              return;
            }
            const ui = await fetch('/admin/ui', {headers: {'Authorization': 'Bearer ' + token}});
            if (!ui.ok) {
              const err = await ui.json().catch(() => ({detail: '无法加载后台页面'}));
              msg.textContent = err.detail || ('无法加载后台页面: ' + ui.status);
              return;
            }
            const html = await ui.text();
            document.open();
            document.write(html);
            document.close();
          } catch (err) {
            msg.textContent = err.toString();
          }
        });
      </script>
    </body>
    </html>
    """
    return HTMLResponse(html)
