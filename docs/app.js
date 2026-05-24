/* Leaderboard interactivity.
   Pure vanilla JS — no frameworks, no build step.
*/

(function () {
  "use strict";

  const DATA = window.LEADERBOARD_DATA;
  if (!DATA) {
    console.error("Leaderboard data missing — make sure data.js loaded.");
    return;
  }

  // ---------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------
  const state = {
    year: "all",
    quarter: "all",
    category: "all",
    search: "",
    expanded: new Set(),
  };

  // ---------------------------------------------------------------------
  // Derived data
  // ---------------------------------------------------------------------
  const ALL_YEARS = (() => {
    const set = new Set();
    DATA.people.forEach((p) =>
      p.activities.forEach((a) => set.add(a.date.slice(0, 4)))
    );
    return [...set].sort().reverse();
  })();

  const ICONS = {
    cap: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M2 9l10-5 10 5-10 5L2 9z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M6 11v4c0 1.5 2.7 3 6 3s6-1.5 6-3v-4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><path d="M22 9v5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
    podium:
      '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="5" y="5" width="14" height="7" rx="1" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><line x1="8" y1="8.5" x2="16" y2="8.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><line x1="12" y1="12" x2="12" y2="18" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><line x1="7" y1="19" x2="17" y2="19" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
    star: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14l-5-4.87 6.91-1.01L12 2z"/></svg>',
  };

  // ---------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------
  const quarterOf = (dateStr) => {
    const m = parseInt(dateStr.slice(5, 7), 10);
    return "Q" + Math.ceil(m / 3);
  };

  const matchesFilters = (activity) => {
    if (state.year !== "all" && !activity.date.startsWith(state.year)) return false;
    if (state.quarter !== "all" && quarterOf(activity.date) !== state.quarter) return false;
    if (state.category !== "all" && activity.category !== state.category) return false;
    return true;
  };

  const totalFor = (person) =>
    person.activities.filter(matchesFilters).reduce((sum, a) => sum + a.points, 0);

  const countsByCategory = (person) => {
    const out = {};
    DATA.categories.forEach((c) => (out[c] = 0));
    person.activities.filter(matchesFilters).forEach((a) => {
      out[a.category] = (out[a.category] || 0) + 1;
    });
    return out;
  };

  const initials = (name) =>
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((n) => n[0].toUpperCase())
      .join("");

  // Deterministic colour per name so the same person always gets the same swatch.
  const PALETTE = [
    ["#0EA5E9", "#0369A1"],
    ["#22C55E", "#15803D"],
    ["#F59E0B", "#B45309"],
    ["#A855F7", "#6D28D9"],
    ["#EF4444", "#B91C1C"],
    ["#14B8A6", "#0F766E"],
    ["#EC4899", "#BE185D"],
    ["#6366F1", "#4338CA"],
  ];
  const colourFor = (name) => {
    let h = 0;
    for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
    return PALETTE[h % PALETTE.length];
  };

  const escapeHtml = (s) =>
    String(s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[c]));

  const formatDate = (iso) => {
    const [y, m, d] = iso.split("-");
    const months = [
      "Jan", "Feb", "Mar", "Apr", "May", "Jun",
      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ];
    return `${d}-${months[parseInt(m, 10) - 1]}-${y}`;
  };

  // ---------------------------------------------------------------------
  // Rendering
  // ---------------------------------------------------------------------
  function renderDropdownOptions() {
    const yearMenu = document.querySelector('.dropdown[data-filter="year"] .dropdown-menu');
    const yearOptions = [
      { value: "all", label: "All Years" },
      ...ALL_YEARS.map((y) => ({ value: y, label: y })),
    ];
    yearMenu.innerHTML = yearOptions
      .map(
        (o) =>
          `<li role="option" data-value="${o.value}" aria-selected="${
            o.value === state.year ? "true" : "false"
          }">${escapeHtml(o.label)}</li>`
      )
      .join("");

    const catMenu = document.querySelector(
      '.dropdown[data-filter="category"] .dropdown-menu'
    );
    const catOptions = [
      { value: "all", label: "All Categories" },
      ...DATA.categories.map((c) => ({ value: c, label: c })),
    ];
    catMenu.innerHTML = catOptions
      .map(
        (o) =>
          `<li role="option" data-value="${o.value}" aria-selected="${
            o.value === state.category ? "true" : "false"
          }">${escapeHtml(o.label)}</li>`
      )
      .join("");
  }

  function renderAvatar(name, sizeClass) {
    const [bg, bg2] = colourFor(name);
    const style = `background: linear-gradient(135deg, ${bg} 0%, ${bg2} 100%);`;
    return `<div class="avatar ${sizeClass}" style="${style}" aria-hidden="true">${escapeHtml(
      initials(name)
    )}</div>`;
  }

  function renderPodium(top3) {
    const podium = document.getElementById("podium");
    if (top3.length === 0) {
      podium.innerHTML = "";
      return;
    }
    // Visual order: 2 — 1 — 3
    const order = [];
    if (top3[1]) order.push({ entry: top3[1], rank: 2 });
    if (top3[0]) order.push({ entry: top3[0], rank: 1 });
    if (top3[2]) order.push({ entry: top3[2], rank: 3 });

    podium.innerHTML = order
      .map(({ entry, rank }) => {
        const sizeClass = rank === 1 ? "size-lg" : "size-md";
        return `
          <div class="podium-slot rank-${rank}" role="listitem">
            <div class="avatar-wrap">
              ${renderAvatar(entry.person.name, sizeClass)}
              <span class="rank-badge" aria-label="Rank ${rank}">${rank}</span>
            </div>
            <div class="name">${escapeHtml(entry.person.name)}</div>
            <div class="role">${escapeHtml(entry.person.role)}</div>
            <div class="points-pill">
              <span class="star">${ICONS.star}</span>
              <span>${entry.total}</span>
            </div>
            <div class="podium-block" aria-hidden="true">${rank}</div>
          </div>`;
      })
      .join("");
  }

  function renderRankingItem(entry, index) {
    const counts = countsByCategory(entry.person);
    const filteredActivities = entry.person.activities
      .filter(matchesFilters)
      .slice()
      .sort((a, b) => (a.date < b.date ? 1 : -1));

    const iconCounts = [
      { key: "Mentorship", icon: ICONS.cap, label: "Mentorship activities" },
      { key: "Talks", icon: ICONS.podium, label: "Talks given" },
    ]
      .filter((c) => counts[c.key] > 0)
      .map(
        (c) => `
          <span class="count" title="${escapeHtml(c.label)}">
            ${c.icon}
            <span>${counts[c.key]}</span>
          </span>`
      )
      .join("");

    const tableRows = filteredActivities
      .map(
        (a) => `
          <tr>
            <td>${escapeHtml(a.title)}</td>
            <td><span class="category-pill">${escapeHtml(a.category)}</span></td>
            <td>${formatDate(a.date)}</td>
            <td class="r points-cell">+${a.points}</td>
          </tr>`
      )
      .join("");

    const expanded = state.expanded.has(entry.person.id);

    return `
      <li class="ranking-item" data-id="${entry.person.id}" data-expanded="${expanded}">
        <div class="row">
          <span class="rank-num">${index + 1}</span>
          ${renderAvatar(entry.person.name, "size-sm")}
          <div class="who">
            <div class="name">${escapeHtml(entry.person.name)}</div>
            <div class="role">${escapeHtml(entry.person.role)}</div>
          </div>
          <div class="icon-counts">${iconCounts}</div>
          <div class="total-block">
            <span class="label">Total</span>
            <span class="points">${ICONS.star}<span>${entry.total}</span></span>
          </div>
          <button class="expand-btn" type="button" aria-expanded="${expanded}" aria-label="Toggle activity for ${escapeHtml(
      entry.person.name
    )}">
            <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
              <path d="M6 9l6 6 6-6" stroke="currentColor" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
        </div>
        <div class="detail" aria-hidden="${!expanded}">
          <div class="inner">
            <div class="detail-body">
              <h4>Recent Activity</h4>
              ${
                tableRows
                  ? `<table class="activity-table">
                       <thead><tr>
                         <th>Activity</th>
                         <th>Category</th>
                         <th>Date</th>
                         <th class="r">Points</th>
                       </tr></thead>
                       <tbody>${tableRows}</tbody>
                     </table>`
                  : `<p class="empty-state">No activities match the current filters.</p>`
              }
            </div>
          </div>
        </div>
      </li>`;
  }

  function applyFilters() {
    const q = state.search.trim().toLowerCase();
    const entries = DATA.people
      .map((person) => ({ person, total: totalFor(person) }))
      .filter((e) => e.total > 0)
      .filter((e) => !q || e.person.name.toLowerCase().includes(q))
      .sort((a, b) => {
        if (b.total !== a.total) return b.total - a.total;
        return a.person.name.localeCompare(b.person.name);
      });
    return entries;
  }

  function renderAll() {
    const entries = applyFilters();
    renderPodium(entries.slice(0, 3));

    const ranking = document.getElementById("ranking");
    if (entries.length === 0) {
      ranking.innerHTML = `<li class="empty-state">No one matches the current filters yet.</li>`;
      return;
    }
    ranking.innerHTML = entries.map((e, i) => renderRankingItem(e, i)).join("");
  }

  // ---------------------------------------------------------------------
  // Event wiring
  // ---------------------------------------------------------------------
  function closeAllDropdowns(except) {
    document.querySelectorAll(".dropdown").forEach((d) => {
      if (d !== except) {
        d.setAttribute("data-open", "false");
        const btn = d.querySelector(".dropdown-toggle");
        if (btn) btn.setAttribute("aria-expanded", "false");
      }
    });
  }

  function wireDropdowns() {
    document.querySelectorAll(".dropdown").forEach((drop) => {
      const filter = drop.dataset.filter;
      const toggle = drop.querySelector(".dropdown-toggle");
      const valueEl = drop.querySelector(".value");
      const menu = drop.querySelector(".dropdown-menu");

      toggle.addEventListener("click", (e) => {
        e.stopPropagation();
        const open = drop.dataset.open === "true";
        closeAllDropdowns(drop);
        drop.setAttribute("data-open", open ? "false" : "true");
        toggle.setAttribute("aria-expanded", open ? "false" : "true");
      });

      menu.addEventListener("click", (e) => {
        const li = e.target.closest("li[role='option']");
        if (!li) return;
        const value = li.dataset.value;
        state[filter] = value;
        valueEl.textContent = li.textContent;
        menu
          .querySelectorAll("li")
          .forEach((opt) =>
            opt.setAttribute(
              "aria-selected",
              opt.dataset.value === value ? "true" : "false"
            )
          );
        drop.setAttribute("data-open", "false");
        toggle.setAttribute("aria-expanded", "false");
        renderAll();
      });

      // keyboard
      toggle.addEventListener("keydown", (e) => {
        if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          drop.setAttribute("data-open", "true");
          toggle.setAttribute("aria-expanded", "true");
          const first = menu.querySelector("li");
          if (first) first.focus();
        } else if (e.key === "Escape") {
          drop.setAttribute("data-open", "false");
          toggle.setAttribute("aria-expanded", "false");
        }
      });
    });

    document.addEventListener("click", () => closeAllDropdowns(null));
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeAllDropdowns(null);
    });
  }

  function wireSearch() {
    const input = document.getElementById("search-input");
    input.addEventListener("input", (e) => {
      state.search = e.target.value;
      renderAll();
    });
  }

  function wireRanking() {
    const ranking = document.getElementById("ranking");
    ranking.addEventListener("click", (e) => {
      const item = e.target.closest(".ranking-item");
      if (!item) return;
      const expandBtn = e.target.closest(".expand-btn");
      const rowClick =
        e.target.closest(".row") && !e.target.closest(".expand-btn");
      if (!expandBtn && !rowClick) return;

      const id = parseInt(item.dataset.id, 10);
      if (state.expanded.has(id)) {
        state.expanded.delete(id);
      } else {
        state.expanded.add(id);
      }
      const willExpand = state.expanded.has(id);
      item.setAttribute("data-expanded", willExpand);
      const btn = item.querySelector(".expand-btn");
      if (btn) btn.setAttribute("aria-expanded", String(willExpand));
      const detail = item.querySelector(".detail");
      if (detail) detail.setAttribute("aria-hidden", String(!willExpand));
    });
  }

  function wireChromeScroll() {
    // Hide the top chrome when the user scrolls down,
    // slide it back into view when they scroll up.
    const chrome = document.querySelector(".sp-chrome");
    if (!chrome) return;
    let lastY = window.scrollY;
    let ticking = false;
    const SHOW_NEAR_TOP = 80;
    const DELTA = 6;

    function update() {
      const y = window.scrollY;
      if (y < SHOW_NEAR_TOP) {
        chrome.classList.remove("is-hidden");
      } else if (y > lastY + DELTA) {
        chrome.classList.add("is-hidden");
      } else if (y < lastY - DELTA) {
        chrome.classList.remove("is-hidden");
      }
      lastY = y;
      ticking = false;
    }

    window.addEventListener(
      "scroll",
      () => {
        if (!ticking) {
          requestAnimationFrame(update);
          ticking = true;
        }
      },
      { passive: true }
    );
  }

  // ---------------------------------------------------------------------
  // Boot
  // ---------------------------------------------------------------------
  document.addEventListener("DOMContentLoaded", () => {
    renderDropdownOptions();
    wireDropdowns();
    wireSearch();
    wireRanking();
    wireChromeScroll();
    renderAll();
  });
})();
