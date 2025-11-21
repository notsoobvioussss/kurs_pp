const CHIPS = ["Все", "Физический доступ", "Кибератаки ICS/SCADA", "Финансы и мошенничество", "Персонал и инсайдеры", "Экология и безопасность"];

const CATEGORY_HINT = {
  "Физический доступ": "Несанкционированное проникновение / кража / саботаж оборудования",
  "Кибератаки ICS/SCADA": "Крипто-вымогательство АСУ ТП / подмена уставок / APT на SCADA",
  "Финансы и мошенничество": "Манипуляция данными ERP/MES, DDoS на биржи, кража транзакций",
  "Персонал и инсайдеры": "Вербовка, фишинг под руководителей, утечки через сотрудников",
  "Экология и безопасность": "Разгерметизация, пожарная безопасность, отключение мониторинга",
  Общее: "Общая информационная угроза без точного отнесения",
};

const THREAT_LIBRARY = [
  {
    title: "Физическая защита",
    items: [
      "Несанкционированное проникновение в серверные и кроссовые",
      "Кража/подмена серверов, СХД и сетевых устройств",
      "Саботаж кабельных трасс, перерезание ВОЛС",
      "Обход СКУД с поддельными пропусками и охранами",
      "Временные зоны работ без контроля (строительные площадки)",
    ],
  },
  {
    title: "ICS / SCADA / OT",
    items: [
      "Подмена контроллеров и прошивок технологического оборудования",
      "Крипто-вымогательские атаки на АСУ ТП добычи/переработки",
      "DDoS и срыв сеансов связи с ГИС ТЭК и диспетчерскими",
      "Подмена уставок и данных в системах ППД, КИПиА",
      "Целевой саботаж SCADA (дистанционные отключения, ложные команды)",
    ],
  },
  {
    title: "Финансы и цепочки поставок",
    items: [
      "Манипуляции с данными планирования (ERP/MES) и кредитных рисков",
      "Срыв операций на товарно-сырьевых биржах (DDoS на торговые площадки)",
      "Подмена маршрутов и логистики, кража данных о транзакциях",
      "Фальсификация документов для ФНС/Роснедра, таможенных деклараций",
      "Использование подставных подрядчиков для внедрения вредоносного ПО",
    ],
  },
  {
    title: "Инсайдеры и персонал",
    items: [
      "Вербовка сотрудников и давление/шантаж для раскрытия доступов",
      "Целевые фишинговые рассылки под видом распоряжений руководства",
      "Психологическая усталость сменных бригад, ошибки под давлением",
      "Нарушение регламентов удаленного доступа и простые пароли",
      "Утечки через мобильные устройства, флешки и печать",
    ],
  },
  {
    title: "Экология и пожарная безопасность",
    items: [
      "Разгерметизация трубопроводов с ЛВЖ/ГГ, выбросы и разрывы",
      "Неисправность АПС/АУПТ, молниезащиты и аварийной вентиляции",
      "Самовозгорание пирофорных отложений, статическое электричество",
      "Блокирование путей эвакуации и отсутствие средств пожаротушения",
      "Целенаправленное повреждение систем экологического мониторинга",
    ],
  },
];

let state = {
  items: [],
  filtered: [],
  category: "Все",
  freshOnly: false,
  sortRecent: true,
  search: "",
  generatedAt: "",
  sources: [],
};

function normalizeText(value) {
  return (value || "")
    .toString()
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim();
}

async function loadData() {
  try {
    const res = await fetch("./data/news.json", { cache: "no-store" });
    const data = await res.json();
    state.items = data.items || [];
    state.generatedAt = data.generated_at;
    state.sources = data.sources || [];
    applyFilters();
  } catch (err) {
    console.error(err);
    document.getElementById("feed").innerHTML =
      '<div class="card"><p>Не удалось загрузить данные. Проверьте, что <code>data/news.json</code> создан.</p></div>';
  }
}

function applyFilters() {
  const now = new Date();
  const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
  const search = normalizeText(state.search);
  let items = [...state.items];

  if (state.category !== "Все") {
    items = items.filter((item) => (item.categories || []).includes(state.category));
  }

  if (state.freshOnly) {
    items = items.filter((item) => {
      if (!item.published) return false;
      const d = new Date(item.published);
      return d >= sevenDaysAgo;
    });
  }

  if (search) {
    items = items.filter((item) => {
      const categories = (item.categories || []).join(" ");
      const blob = normalizeText([item.title, item.summary, item.source, categories].join(" "));
      return blob && blob.includes(search);
    });
  }

  items = items.map((item) => ({
    ...item,
    published: item.published || "",
  }));

  if (state.sortRecent) {
    items.sort((a, b) => new Date(b.published) - new Date(a.published));
  }

  state.filtered = items.slice(0, 120); // keep UI snappy
  renderStats();
  renderFeed();
}

function renderStats() {
  const freshCount = state.items.filter((item) => {
    if (!item.published) return false;
    const d = new Date(item.published);
    return (Date.now() - d.getTime()) / (1000 * 60 * 60) <= 72;
  }).length;

  document.getElementById("stat-new").textContent = freshCount;
  document.getElementById("stat-total").textContent = state.items.length;
  document.getElementById("stat-sources").textContent = state.sources.length;

  const gen = state.generatedAt
    ? `Обновлено: ${new Date(state.generatedAt).toLocaleString("ru-RU")}`
    : "—";
  document.getElementById("stat-generated").textContent = gen;
}

function renderCategories() {
  const container = document.getElementById("category-chips");
  container.innerHTML = "";
  CHIPS.forEach((name) => {
    const el = document.createElement("button");
    el.className = `chip ${state.category === name ? "active" : ""}`;
    el.textContent = name;
    el.onclick = () => {
      state.category = name;
      applyFilters();
      renderCategories();
    };
    container.appendChild(el);
  });
}

function renderFeed() {
  const feed = document.getElementById("feed");
  if (!state.filtered.length) {
    feed.innerHTML = '<div class="card"><p>Нет кейсов по этим фильтрам.</p></div>';
    return;
  }

  feed.innerHTML = state.filtered
    .map((item) => {
      const date = item.published ? new Date(item.published).toLocaleString("ru-RU") : "—";
      const categories = (item.categories || []).map((c) => `<span class="pill orange">${c}</span>`).join("");
      const threatLabel = (item.categories || []).map((c) => CATEGORY_HINT[c] || CATEGORY_HINT["Общее"]).join(" · ") || CATEGORY_HINT["Общее"];
      return `
        <article class="card">
          <div class="card-header">
            <h3 class="card-title">${item.title}</h3>
            <div class="card-meta">
              <span class="pill cyan">${item.source}</span>
              <span>${date}</span>
            </div>
          </div>
          <p>${item.summary || "Нет описания"}</p>
          <p class="threat-label">Угроза из списка: ${threatLabel}</p>
          <div class="card-footer">
            ${categories}
            <a class="pill" style="text-decoration:none" href="${item.link}" target="_blank" rel="noopener">Читать</a>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderThreatMatrix() {
  const root = document.getElementById("matrix");
  root.innerHTML = THREAT_LIBRARY.map(
    (block) => `
      <div class="matrix-card">
        <h3>${block.title}</h3>
        <ul>
          ${block.items.map((i) => `<li>${i}</li>`).join("")}
        </ul>
      </div>
    `
  ).join("");
}

function bindControls() {
  document.getElementById("search").addEventListener("input", (e) => {
    state.search = e.target.value;
    applyFilters();
  });

  document.getElementById("freshOnly").addEventListener("change", (e) => {
    state.freshOnly = e.target.checked;
    applyFilters();
  });

  document.getElementById("sortRecent").addEventListener("change", (e) => {
    state.sortRecent = e.target.checked;
    applyFilters();
  });

  document.getElementById("refresh").addEventListener("click", () => loadData());
}

renderCategories();
renderThreatMatrix();
bindControls();
loadData();
