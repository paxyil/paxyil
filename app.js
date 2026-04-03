const tg = window.Telegram.WebApp;
tg.expand();

const api = {
  headers() {
    return {
      "X-Telegram-Init-Data": tg.initData || ""
    };
  },

  async me() {
    const res = await fetch("/api/me", { headers: this.headers() });
    return res.json();
  },

  async applications(status = "") {
    const url = status ? `/api/applications?status=${status}` : `/api/applications`;
    const res = await fetch(url, { headers: this.headers() });
    return res.json();
  },

  async application(id) {
    const res = await fetch(`/api/applications/${id}`, { headers: this.headers() });
    return res.json();
  },

  async createApplication(formData) {
    const res = await fetch("/api/applications", {
      method: "POST",
      headers: this.headers(),
      body: formData
    });
    return res.json();
  },

  async sendMessage(id, text) {
    const fd = new FormData();
    fd.append("text", text);

    const res = await fetch(`/api/applications/${id}/messages`, {
      method: "POST",
      headers: this.headers(),
      body: fd
    });
    return res.json();
  },

  async setStatus(id, status) {
    const fd = new FormData();
    fd.append("status", status);

    const res = await fetch(`/api/applications/${id}/status`, {
      method: "POST",
      headers: this.headers(),
      body: fd
    });
    return res.json();
  }
};

const screens = {
  home: document.getElementById("screen-home"),
  detail: document.getElementById("screen-detail")
};
const tabs = document.getElementById("tabs");
const roleBadge = document.getElementById("roleBadge");

let me = null;
let currentApplicationId = null;

function statusText(status) {
  if (status === "new") return "Новая";
  if (status === "in_progress") return "В работе";
  if (status === "closed") return "Закрыта";
  return status;
}

function showScreen(name) {
  Object.values(screens).forEach(el => el.classList.remove("active"));
  screens.home.classList.add("hidden");
  screens.detail.classList.add("hidden");

  if (name === "home") screens.home.classList.remove("hidden");
  if (name === "detail") screens.detail.classList.remove("hidden");
}

function renderTabs() {
  const tabList = me.is_admin
    ? [
        ["all", "Все"],
        ["new", "Новые"],
        ["in_progress", "В работе"],
        ["closed", "Закрытые"]
      ]
    : [
        ["all", "Мои заявки"],
        ["create", "Новая заявка"]
      ];

  tabs.innerHTML = "";
  tabList.forEach(([key, title]) => {
    const btn = document.createElement("button");
    btn.className = "tab-btn";
    btn.textContent = title;
    btn.onclick = () => {
      document.querySelectorAll(".tab-btn").forEach(x => x.classList.remove("active"));
      btn.classList.add("active");

      if (key === "create") {
        renderCreateForm();
      } else {
        loadApplications(key === "all" ? "" : key);
      }
    };
    tabs.appendChild(btn);
  });

  tabs.querySelector(".tab-btn")?.classList.add("active");
}

function renderCreateForm() {
  showScreen("home");
  screens.home.innerHTML = `
    <div class="card">
      <h2>Оставить заявку</h2>
      <div class="grid two">
        <input id="name" placeholder="Ваше имя" />
        <input id="phone" placeholder="+7 (___) ___-__-__" />
      </div>
      <div class="grid two" style="margin-top:12px;">
        <select id="service">
          <option value="Telegram bot">Telegram bot</option>
          <option value="Mini App">Mini App</option>
          <option value="CRM bot">CRM bot</option>
          <option value="Парсер">Парсер</option>
          <option value="Другое">Другое</option>
        </select>
        <input id="desired_date" type="date" />
      </div>
      <div class="grid two" style="margin-top:12px;">
        <input id="desired_time" type="time" />
        <input id="photo" type="file" accept="image/*" />
      </div>
      <div style="margin-top:12px;">
        <textarea id="comment" placeholder="Опишите задачу"></textarea>
      </div>
      <div class="actions">
        <button class="btn primary" id="createBtn">Создать заявку</button>
      </div>
    </div>
  `;

  const phone = document.getElementById("phone");
  phone.addEventListener("input", phoneMask);

  document.getElementById("createBtn").onclick = async () => {
    const fd = new FormData();
    fd.append("name", document.getElementById("name").value.trim());
    fd.append("phone", document.getElementById("phone").value.trim());
    fd.append("service", document.getElementById("service").value);
    fd.append("desired_date", document.getElementById("desired_date").value);
    fd.append("desired_time", document.getElementById("desired_time").value);
    fd.append("comment", document.getElementById("comment").value.trim());

    const file = document.getElementById("photo").files[0];
    if (file) fd.append("photo", file);

    const result = await api.createApplication(fd);
    if (result.ok) {
      tg.showAlert(`Заявка #${result.application_id} создана`);
      loadApplications();
    } else {
      tg.showAlert("Ошибка создания заявки");
    }
  };
}

function phoneMask(e) {
  let x = e.target.value.replace(/\D/g, "").slice(0, 11);
  if (x.startsWith("8")) x = "7" + x.slice(1);
  if (!x.startsWith("7")) x = "7" + x;

  let out = "+7";
  if (x.length > 1) out += " (" + x.slice(1, 4);
  if (x.length >= 4) out += ")";
  if (x.length > 4) out += " " + x.slice(4, 7);
  if (x.length > 7) out += "-" + x.slice(7, 9);
  if (x.length > 9) out += "-" + x.slice(9, 11);

  e.target.value = out;
}

async function loadApplications(status = "") {
  showScreen("home");
  const items = await api.applications(status);

  screens.home.innerHTML = `
    <div class="card">
      <h2>${me.is_admin ? "Заявки" : "Мои заявки"}</h2>
      <div id="list"></div>
    </div>
  `;

  const list = document.getElementById("list");

  if (!items.length) {
    list.innerHTML = `<div class="muted">Ничего не найдено</div>`;
    return;
  }

  list.innerHTML = items.map(item => `
    <div class="card list-item">
      <div>
        <div><b>#${item.id}</b> — ${item.service}</div>
        <div class="muted">${item.user_name}</div>
      </div>
      <div class="actions">
        <span class="status ${item.status}">${statusText(item.status)}</span>
        <button class="btn" onclick="openApplication(${item.id})">Открыть</button>
      </div>
    </div>
  `).join("");
}

async function openApplication(id) {
  currentApplicationId = id;
  const data = await api.application(id);
  const app = data.application;
  const messages = data.messages;

  showScreen("detail");
  screens.detail.innerHTML = `
    <div class="card">
      <div class="actions">
        <button class="btn" onclick="backHome()">← Назад</button>
        ${me.is_admin ? `
          <button class="btn primary" onclick="changeStatus('in_progress')">В работу</button>
          <button class="btn success" onclick="changeStatus('closed')">Закрыть</button>
          <button class="btn" onclick="changeStatus('new')">Переоткрыть</button>
        ` : ""}
      </div>

      <h2>Заявка #${app.id}</h2>
      <div class="grid two">
        <div class="card">
          <div><b>Клиент:</b> ${app.user_name}</div>
          <div><b>Телефон:</b> ${app.phone}</div>
          <div><b>Услуга:</b> ${app.service}</div>
          <div><b>Дата:</b> ${app.desired_date || "—"}</div>
          <div><b>Время:</b> ${app.desired_time || "—"}</div>
          <div><b>Статус:</b> ${statusText(app.status)}</div>
          <div style="margin-top:8px;"><b>Комментарий:</b><br>${app.comment}</div>
          ${app.photo_path ? `<img src="${app.photo_path}" style="margin-top:10px;max-width:100%;border-radius:12px;">` : ""}
        </div>

        <div class="card">
          <div class="chat" id="chat">
            ${messages.map(m => `
              <div class="msg ${m.sender_role}">
                <div>${m.text}</div>
                <div class="muted" style="margin-top:6px;font-size:12px;">${m.created_at}</div>
              </div>
            `).join("")}
          </div>

          <div class="actions" style="margin-top:12px;">
            <textarea id="msgText" placeholder="Введите сообщение"></textarea>
            <button class="btn primary" onclick="sendMessage()">Отправить</button>
          </div>
        </div>
      </div>
    </div>
  `;
}

function backHome() {
  loadApplications();
}

async function sendMessage() {
  const text = document.getElementById("msgText").value.trim();
  if (!text) return;
  await api.sendMessage(currentApplicationId, text);
  openApplication(currentApplicationId);
}

async function changeStatus(status) {
  await api.setStatus(currentApplicationId, status);
  openApplication(currentApplicationId);
}

window.openApplication = openApplication;
window.backHome = backHome;
window.sendMessage = sendMessage;
window.changeStatus = changeStatus;

async function bootstrap() {
  me = await api.me();
  roleBadge.textContent = me.is_admin ? "admin" : "user";
  renderTabs();
  loadApplications();
}

bootstrap();