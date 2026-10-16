import datetime
import json
import os
import random
import flet as ft

# Ścieżka zapisu danych
DATA_FILE = os.path.expanduser("~/betmaster_data.json")


def load_data():
  if not os.path.exists(DATA_FILE):
    return []
  with open(DATA_FILE, "r", encoding="utf-8") as f:
    try:
      return json.load(f)
    except Exception:
      return []


def save_data(data):
  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)


def main(page: ft.Page):
  page.title = "BetMaster Pro - Banger Edition"
  page.theme_mode = ft.ThemeMode.DARK
  page.padding = 0
  page.scroll = ft.ScrollMode.AUTO

  # --- KONTROLKI I ELEMENTY ---
  goal_input = ft.TextField(
      label="🎯 Cel Zysku (zł)",
      value="500",
      width=140,
      text_align=ft.TextAlign.RIGHT,
      text_size=13,
      border_color="#10b981",
  )
  summary_text = ft.Text("", size=12, weight=ft.FontWeight.BOLD)
  coupons_list = ft.ListView(expand=1, spacing=10, padding=5)

  title_input = ft.TextField(
      label="Opis Kuponu / Mecze", hint_text="np. Real - Barca Over 2.5"
  )
  sport_dropdown = ft.Dropdown(
      label="Dyscyplina",
      value="Piłka Nożna",
      options=[
          ft.dropdown.Option("Piłka Nożna"),
          ft.dropdown.Option("Tenis (ATP/WTA)"),
          ft.dropdown.Option("Koszykówka (NBA)"),
          ft.dropdown.Option("Hokej (NHL)"),
          ft.dropdown.Option("Esport"),
          ft.dropdown.Option("Inne"),
      ],
  )
  stake_input = ft.TextField(label="Stawka (zł)", hint_text="50")
  odds_input = ft.TextField(label="Kurs Łączny (AKO)", hint_text="2.15")
  match_id_input = ft.TextField(
      label="ID Flashscore (mid=...)", hint_text="opcjonalnie"
  )
  status_dropdown = ft.Dropdown(
      label="Status Początkowy",
      value="⏳ W grze (PENDING)",
      options=[
          ft.dropdown.Option("⏳ W grze (PENDING)"),
          ft.dropdown.Option("✅ Wygrana (WIN)"),
          ft.dropdown.Option("❌ Przegrana (LOST)"),
      ],
  )
  error_text = ft.Text("", color=ft.colors.RED_400)

  scanner_box = ft.TextField(
      multiline=True,
      read_only=True,
      min_lines=13,
      max_lines=18,
      text_size=12,
  )

  # Kontrolki kalkulatora kontry
  hedge_stake_orig = ft.TextField(
      label="Stawka 1. kuponu (zł)", hint_text="100", width=150
  )
  hedge_odds_orig = ft.TextField(
      label="Kurs 1. kuponu", hint_text="3.50", width=150
  )
  hedge_odds_opp = ft.TextField(
      label="Kurs kontry na żywo", hint_text="2.10", width=150
  )
  hedge_result_text = ft.Text(
      "Wpisz dane wyżej, aby wyliczyć kontrę.",
      size=12,
      color="#34d399",
  )

  # --- LOGIKA APLIKACJI ---
  def refresh_history():
    coupons_list.controls.clear()
    data = load_data()
    if not data:
      summary_text.value = "🚀 Brak kuponów w historii. Dodaj swój pierwszy bet w zakładce 'Dodaj'!"
      page.update()
      return

    total_spent = sum(b["stake"] for b in data)
    closed = [b for b in data if b["status"] in ["WIN", "LOST"]]
    closed_spent = sum(b["stake"] for b in closed)

    total_won = sum(
        (b["stake"] * 0.88 * b["odds"]) for b in closed if b["status"] == "WIN"
    )
    total_lost_amount = sum(b["stake"] for b in closed if b["status"] == "LOST")
    net_profit = sum(b["profit"] for b in closed)
    wins = sum(1 for b in closed if b["status"] == "WIN")
    win_rate = (wins / len(closed)) * 100 if closed else 0.0
    roi = (net_profit / closed_spent) * 100 if closed_spent > 0 else 0.0

    try:
      target_goal = float(goal_input.value.strip().replace(",", "."))
    except ValueError:
      target_goal = 500.0

    progress_pct = (net_profit / target_goal) * 100 if target_goal > 0 else 0.0
    progress_pct = max(0.0, min(100.0, progress_pct))

    summary_text.value = (
        f"💵 Wkład: {total_spent:.2f} zł  |  ❌ Przegrane: -{total_lost_amount:.2f} zł\n"
        f"🏆 Wygrane netto (po tax 12%): +{total_won:.2f} zł\n"
        f"📈 ZYSK NETTO: {net_profit:+.2f} zł  |  ROI: {roi:.1f}%  |  Winrate: {win_rate:.1f}%\n"
        f"🎯 Cel ({target_goal:.0f} zł): Realizacja w {progress_pct:.1f}%"
    )

    for index, item in enumerate(reversed(data)):
      real_idx = len(data) - 1 - index
      status_icon = (
          "⏳"
          if item["status"] == "PENDING"
          else ("✅" if item["status"] == "WIN" else "❌")
      )
      bg_color = (
          ft.colors.with_opacity(0.25, ft.colors.BLUE_GREY_900)
          if item["status"] == "PENDING"
          else (
              ft.colors.with_opacity(0.35, ft.colors.GREEN_900)
              if item["status"] == "WIN"
              else ft.colors.with_opacity(0.35, ft.colors.RED_900)
          )
      )

      match_str = f" | Flashscore: {item['match_id']}" if item.get("match_id") else ""
      card_info = ft.Column([
          ft.Text(
              f"{status_icon} [{item['sport']}] {item['title']}{match_str}",
              weight=ft.FontWeight.BOLD,
              size=13,
              color=ft.colors.WHITE,
          ),
          ft.Text(
              f"Stawka: {item['stake']} zł | Kurs: {item['odds']} | Profit: {item['profit']:+.2f} zł",
              size=11,
              color=ft.colors.GREY_300,
          ),
      ], spacing=2)

      actions = []
      if item["status"] == "PENDING":
        actions.extend([
            ft.ElevatedButton(
                "WIN",
                bgcolor="#059669",
                color=ft.colors.WHITE,
                scale=0.8,
                on_click=lambda e, idx=real_idx: update_coupon_status(
                    idx, "WIN"
                ),
            ),
            ft.ElevatedButton(
                "LOST",
                bgcolor=ft.colors.RED_600,
                color=ft.colors.WHITE,
                scale=0.8,
                on_click=lambda e, idx=real_idx: update_coupon_status(
                    idx, "LOST"
                ),
            ),
        ])
      actions.append(
          ft.IconButton(
              icon=ft.icons.DELETE_OUTLINED,
              icon_size=18,
              icon_color=ft.colors.GREY_500,
              on_click=lambda e, idx=real_idx: delete_coupon(idx),
          )
      )

      card = ft.Container(
          content=ft.Row(
              [
                  ft.Container(content=card_info, expand=True),
                  ft.Row(actions, spacing=0),
              ],
              alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
          ),
          bgcolor=bg_color,
          padding=10,
          border_radius=10,
          border=ft.border.all(1, ft.colors.WHITE12),
      )
      coupons_list.controls.append(card)
    page.update()

  def update_coupon_status(idx, new_status):
    data = load_data()
    data[idx]["status"] = new_status
    stake = data[idx]["stake"]
    odds = data[idx]["odds"]
    if new_status == "WIN":
      data[idx]["profit"] = round((stake * 0.88 * odds) - stake, 2)
    else:
      data[idx]["profit"] = -stake
    save_data(data)
    refresh_history()

  def delete_coupon(idx):
    data = load_data()
    data.pop(idx)
    save_data(data)
    refresh_history()

  def save_coupon_click(e):
    try:
      title = title_input.value.strip()
      if not title:
        error_text.value = "❌ Uzupełnij opis kuponu!"
        page.update()
        return
      stake = float(stake_input.value.strip().replace(",", "."))
      odds = float(odds_input.value.strip().replace(",", "."))
      if stake <= 0 or odds <= 1.0:
        error_text.value = "❌ Błędne parametry stawki lub kursu!"
        page.update()
        return

      status_raw = status_dropdown.value
      if "Wygrana" in status_raw:
        status = "WIN"
        profit = round((stake * 0.88 * odds) - stake, 2)
      elif "Przegrana" in status_raw:
        status = "LOST"
        profit = -stake
      else:
        status = "PENDING"
        profit = 0.0

      data = load_data()
      data.append({
          "id": len(data) + 1,
          "title": title,
          "sport": sport_dropdown.value,
          "stake": stake,
          "odds": odds,
          "match_id": match_id_input.value.strip(),
          "status": status,
          "profit": profit,
      })
      save_data(data)

      title_input.value = ""
      stake_input.value = ""
      odds_input.value = ""
      match_id_input.value = ""
      error_text.value = ""
      go_to_tab(0)
    except ValueError:
      error_text.value = "❌ Błąd wprowadzania liczb!"
      page.update()

  def fetch_scanner(e=None):
    now = datetime.datetime.now()
    current_date = now.strftime("%d.%m.%Y")

    matches_pool = [
        ("Arsenal – West Ham", "Arsenal wygra", 1.45, "Piłka"),
        ("Liverpool – Brighton", "BTTS - TAK", 1.55, "Piłka"),
        ("Lech Poznań – Cracovia", "Over 2.5 gola", 1.70, "Piłka"),
        ("Jagiellonia – Pogoń Szczecin", "Obie strzelą", 1.62, "Piłka"),
        ("Iga Świątek – A. Sabalenka", "Świątek wygra mecz", 1.52, "Tenis"),
        ("H. Hurkacz – M. Berrettini", "Over 22.5 gemów", 1.75, "Tenis"),
        ("LA Lakers – GS Warriors", "Over 224.5 pkt", 1.85, "NBA"),
        ("Boston Bruins – NY Rangers", " Bruins 1X", 1.48, "NHL"),
    ]
    selected = random.sample(matches_pool, 3)
    ako_dublet = round(selected[0][2] * selected[1][2], 2)

    scanner_box.value = (
        f"🔥 PROPOZYCJE SKANERA [{current_date}]\n"
        + "═" * 32
        + f"\n\n🎯 DUBLET DNIA (AKO: ~{ako_dublet:.2f}):\n"
        f" 1. [{selected[0][3]}] {selected[0][0]}\n    Typ: {selected[0][1]} (Kurs: {selected[0][2]:.2f})\n"
        f" 2. [{selected[1][3]}] {selected[1][0]}\n    Typ: {selected[1][1]} (Kurs: {selected[1][2]:.2f})\n\n"
        + "─" * 32
        + f"\n💎 SURE SHOT SINGIEL:\n"
        f" • [{selected[2][3]}] {selected[2][0]}\n   Typ: {selected[2][1]} (Kurs: {selected[2][2]:.2f})\n\n"
        + "═" * 32
        + "\n💡 Pamiętaj: Skaner ułatwia selekcję, zawsze sprawdzaj składy!"
    )
    page.update()

  def calculate_hedge(e):
    try:
      s1 = float(hedge_stake_orig.value.strip().replace(",", "."))
      o1 = float(hedge_odds_orig.value.strip().replace(",", "."))
      o2 = float(hedge_odds_opp.value.strip().replace(",", "."))

      payout1 = s1 * 0.88 * o1  # Zysk brutto po podatku
      hedge_stake = payout1 / o2
      profit_if_win_orig = payout1 - s1 - hedge_stake
      profit_if_win_hedge = (hedge_stake * 0.88 * o2) - s1 - hedge_stake

      hedge_result_text.value = (
          f"➡️ Postaw na kontrę: {hedge_stake:.2f} zł\n"
          f"💰 Zysk opcja A (główny kupon): {profit_if_win_orig:+.2f} zł\n"
          f"🛡️ Zysk opcja B (kontra): {profit_if_win_hedge:+.2f} zł"
      )
    except Exception:
      hedge_result_text.value = "❌ Wpisz prawidłowe liczby!"
    page.update()

  fetch_scanner()

  # --- WIDOKI ZAKŁADEK ---

  # 1. Dziennik
  history_view = ft.Column(
      [
          ft.Row(
              [
                  goal_input,
                  ft.ElevatedButton(
                      "Przelicz",
                      on_click=lambda e: refresh_history(),
                      height=40,
                      bgcolor="#059669",
                      color=ft.colors.WHITE,
                  ),
              ],
              alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
          ),
          summary_text,
          ft.Divider(color=ft.colors.WHITE24),
          coupons_list,
      ],
      expand=True,
  )

  # 2. Dodaj kupon
  add_view = ft.Column(
      [
          ft.Text("➕ Dodaj Kupon do Dziennika", size=18, weight=ft.FontWeight.BOLD),
          title_input,
          sport_dropdown,
          ft.Row(
              [
                  ft.Container(content=stake_input, expand=True),
                  ft.Container(content=odds_input, expand=True),
              ]
          ),
          match_id_input,
          status_dropdown,
          error_text,
          ft.ElevatedButton(
              "Zapisz Kupon",
              bgcolor="#059669",
              color=ft.colors.WHITE,
              width=320,
              height=45,
              on_click=save_coupon_click,
          ),
      ],
      spacing=10,
  )

  # 3. Skaner Live
  scanner_view = ft.Column(
      [
          ft.Row(
              [
                  ft.Text("🔍 Skaner & Typy Live", size=16, weight=ft.FontWeight.BOLD),
                  ft.IconButton(ft.icons.REFRESH, on_click=fetch_scanner, icon_color="#34d399"),
              ],
              alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
          ),
          scanner_box,
      ]
  )

  # 4. Protipy & Kalkulator Kontry
  tips_view = ft.Column(
      [
          ft.Text("🧠 Protipy & Kalkulator Kontry", size=18, weight=ft.FontWeight.BOLD),
          ft.Text("🛡️ Kalkulator Kontry (Hedging):", size=14, weight=ft.FontWeight.BOLD, color="#34d399"),
          ft.Row([hedge_stake_orig, hedge_odds_orig]),
          ft.Row([
              hedge_odds_opp,
              ft.ElevatedButton(
                  "Oblicz",
                  on_click=calculate_hedge,
                  height=45,
                  bgcolor="#059669",
                  color=ft.colors.WHITE,
              ),
          ]),
          hedge_result_text,
          ft.Divider(color=ft.colors.WHITE24),
          ft.Text("💡 Złote Zasady Profesjonalnego Grania:", size=14, weight=ft.FontWeight.BOLD, color="#34d399"),
          ft.Text(
              "1. Graj Single lub Dublety (AKO max ~2.50) – taśmy to domena bukmachera.\n"
              "2. Zarządzanie Kapitałem – stawka pojedyncza nie powinna przekraczać 2-5% Twojego budżetu.\n"
              "3. Ignoruj emocje i odgrywanie się – straciłeś? Zrób przerwę i przemyśl analizę.\n"
              "4. Szukaj wartości (Valuebet) – graj tam, gdzie kurs jest wyższy niż realne ryzyko.",
              size=11,
              color=ft.colors.GREY_300,
          ),
      ],
      spacing=10,
  )

  # 5. Linki i Analiza
  def open_link(url):
    page.launch_url(url)

  analysis_view = ft.Column(
      [
          ft.Text("🔗 Centrum Analizy Sportowej", size=18, weight=ft.FontWeight.BOLD),
          ft.Text("Szybkie przekierowania do portali z danymi:", size=12, color=ft.colors.GREY_400),
          ft.Divider(color=ft.colors.WHITE24),
          ft.ElevatedButton(
              "📊 Flashscore (Wyniki na żywo)",
              icon=ft.icons.SPORTS_SOCCER,
              width=320,
              on_click=lambda e: open_link("https://www.flashscore.pl"),
          ),
          ft.ElevatedButton(
              "🎾 Tenis Explorer / Wyniki Tenis",
              icon=ft.icons.SPORTS_TENNIS,
              width=320,
              on_click=lambda e: open_link("https://www.flashtennis.pl"),
          ),
          ft.ElevatedButton(
              "📈 Sofascore (Statystyki & xG)",
              icon=ft.icons.ANALYTICS,
              width=320,
              on_click=lambda e: open_link("https://www.sofascore.com/pl/"),
          ),
          ft.ElevatedButton(
              "📉 OddsPortal (Porównywarka Kursów)",
              icon=ft.icons.TRENDING_UP,
              width=320,
              on_click=lambda e: open_link("https://www.oddsportal.com"),
          ),
      ],
      spacing=12,
      horizontal_alignment=ft.CrossAxisAlignment.CENTER,
  )

  body_container = ft.Container(content=history_view, expand=True, padding=12)

  def go_to_tab(idx):
    nav_bar.selected_index = idx
    if idx == 0:
      body_container.content = history_view
      refresh_history()
    elif idx == 1:
      body_container.content = add_view
    elif idx == 2:
      body_container.content = scanner_view
    elif idx == 3:
      body_container.content = tips_view
    elif idx == 4:
      body_container.content = analysis_view
    page.update()

  nav_bar = ft.NavigationBar(
      selected_index=0,
      on_change=lambda e: go_to_tab(e.control.selected_index),
      bgcolor="#0B132B",
      destinations=[
          ft.NavigationDestination(icon=ft.icons.BOOK_OUTLINED, selected_icon=ft.icons.BOOK, label="Dziennik"),
          ft.NavigationDestination(icon=ft.icons.ADD_CIRCLE_OUTLINE, selected_icon=ft.icons.ADD_CIRCLE, label="Dodaj"),
          ft.NavigationDestination(icon=ft.icons.SEARCH, label="Skaner"),
          ft.NavigationDestination(icon=ft.icons.PSYCHOLOGY_OUTLINED, selected_icon=ft.icons.PSYCHOLOGY, label="Protipy"),
          ft.NavigationDestination(icon=ft.icons.EXPLORE_OUTLINED, selected_icon=ft.icons.EXPLORE, label="Analiza"),
      ],
  )

  page.navigation_bar = nav_bar

  # Stylizacja tla aplikacji (Dark Cyan / Neon Mint vibe)
  root_background = ft.Container(
      content=body_container,
      gradient=ft.LinearGradient(
          begin=ft.alignment.top_left,
          end=ft.alignment.bottom_right,
          colors=["#0B132B", "#1C2541", "#000814"],
      ),
      expand=True,
  )

  page.add(root_background)
  refresh_history()


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 8550))
  ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port, host="0.0.0.0")
