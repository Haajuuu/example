import datetime
import json
import os
import random
import flet as ft

# Ścieżka zapisu danych w katalogu domowym użytkownika
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
  page.title = "BetMaster Pro"
  page.theme_mode = ft.ThemeMode.DARK
  page.padding = 0
  page.scroll = ft.ScrollMode.AUTO

  # Formularz i kontrolki
  goal_input = ft.TextField(
      label="🎯 Cel Zysku (zł)",
      value="500",
      width=130,
      text_align=ft.TextAlign.RIGHT,
      text_size=13,
  )
  summary_text = ft.Text("", size=12, weight=ft.FontWeight.BOLD)
  coupons_list = ft.ListView(expand=1, spacing=8, padding=5)

  title_input = ft.TextField(
      label="Opis Kuponu / Mecze", hint_text="np. Lech - Cracovia BTTS"
  )
  sport_dropdown = ft.Dropdown(
      label="Dyscyplina",
      value="Piłka Nożna",
      options=[
          ft.dropdown.Option("Piłka Nożna"),
          ft.dropdown.Option("Tenis"),
          ft.dropdown.Option("Hokej (NHL)"),
          ft.dropdown.Option("Koszykówka (NBA)"),
          ft.dropdown.Option("Esport"),
          ft.dropdown.Option("Inne"),
      ],
  )
  stake_input = ft.TextField(label="Stawka (zł)", hint_text="50")
  odds_input = ft.TextField(label="Kurs Łączny (AKO)", hint_text="2.15")
  match_id_input = ft.TextField(
      label="ID Flashscore (mid=...)", hint_text="np. bakVPDoT"
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
      min_lines=12,
      max_lines=18,
      text_size=12,
  )

  def refresh_history():
    coupons_list.controls.clear()
    data = load_data()
    if not data:
      summary_text.value = (
          "Brak zapisanych kuponów. Dodaj pierwszy w zakładce 'Dodaj'!"
      )
      page.update()
      return

    total_spent = sum(b["stake"] for b in data)
    closed = [b for b in data if b["status"] in ["WIN", "LOST"]]
    closed_spent = sum(b["stake"] for b in closed)

    # Podatek 12%
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
        f"💰 Wydano: {total_spent:.2f} zł | Przegrane: -{total_lost_amount:.2f} zł\n"
        f"Wygrane (netto po tax 12%): +{total_won:.2f} zł\n"
        f"📊 ZYSK NETTO: {net_profit:+.2f} zł | ROI: {roi:.1f}% | Skuteczność: {win_rate:.1f}%\n"
        f"🎯 Cel ({target_goal:.0f} zł): Postęp {progress_pct:.1f}%"
    )

    for index, item in enumerate(reversed(data)):
      real_idx = len(data) - 1 - index
      status_icon = (
          "⏳"
          if item["status"] == "PENDING"
          else ("✅" if item["status"] == "WIN" else "❌")
      )
      bg_color = (
          ft.colors.with_opacity(0.4, ft.colors.GREY_900)
          if item["status"] == "PENDING"
          else (
              ft.colors.with_opacity(0.5, ft.colors.GREEN_900)
              if item["status"] == "WIN"
              else ft.colors.with_opacity(0.5, ft.colors.RED_900)
          )
      )

      match_str = f" | Flashscore: {item['match_id']}" if item.get("match_id") else ""
      card_info = ft.Column([
          ft.Text(
              f"{status_icon} [{item['sport']}] {item['title']}{match_str}",
              weight=ft.FontWeight.BOLD,
              size=13,
          ),
          ft.Text(
              f"Stawka: {item['stake']} zł | Kurs: {item['odds']} | Zysk/Strata: {item['profit']:+.2f} zł",
              size=11,
          ),
      ], spacing=2)

      actions = []
      if item["status"] == "PENDING":
        actions.extend([
            ft.ElevatedButton(
                "WIN",
                bgcolor=ft.colors.GREEN_700,
                color=ft.colors.WHITE,
                scale=0.75,
                on_click=lambda e, idx=real_idx: update_coupon_status(idx, "WIN"),
            ),
            ft.ElevatedButton(
                "LOST",
                bgcolor=ft.colors.RED_700,
                color=ft.colors.WHITE,
                scale=0.75,
                on_click=lambda e, idx=real_idx: update_coupon_status(
                    idx, "LOST"
                ),
            ),
        ])
      actions.append(
          ft.IconButton(
              icon=ft.icons.DELETE,
              icon_size=18,
              icon_color=ft.colors.GREY_400,
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
          padding=8,
          border_radius=8,
          border=ft.border.all(1, ft.colors.WHITE10),
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
        error_text.value = "❌ Wpisz opis kuponu!"
        page.update()
        return
      stake = float(stake_input.value.strip().replace(",", "."))
      odds = float(odds_input.value.strip().replace(",", "."))
      if stake <= 0 or odds <= 1.0:
        error_text.value = "❌ Błędna stawka lub kurs!"
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
      error_text.value = "❌ Błąd formatu (używaj cyfr w stawce i kursie)!"
      page.update()

  def fetch_scanner(e=None):
    now = datetime.datetime.now()
    current_date = now.strftime("%d.%m.%Y")
    
    pairs = [
        ("Arsenal – West Ham", "Arsenal wygra", 1.45),
        ("Liverpool – Brighton", "BTTS - TAK", 1.55),
        ("Lech Poznań – Cracovia", "Obie strzelą", 1.65),
        ("Jagiellonia – Pogoń Szczecin", "Over 2.5 gola", 1.60),
        ("Real Madryt – Real Betis", "Real Madryt wygra", 1.38),
        ("FC Barcelona – Sevilla", "Barcelona over 1.5 gola", 1.42),
        ("Inter Mediolan – Lazio", "1X i over 1.5", 1.48),
        ("Bayern Monachium – VfB Stuttgart", "Over 3.0 goli", 1.52),
    ]
    selected = random.sample(pairs, 2)
    ako = round(selected[0][2] * selected[1][2], 2)

    scanner_box.value = (
        f"🎯 DUBLET DNIA [{current_date}]\n"
        + "=" * 32
        + f"\n\n1. {selected[0][0]}\n   Typ: {selected[0][1]} [Kurs: {selected[0][2]:.2f}]\n\n"
        f"2. {selected[1][0]}\n   Typ: {selected[1][1]} [Kurs: {selected[1][2]:.2f}]\n\n"
        f"➡️ SZACOWANE AKO: {ako:.2f}\n"
        + "=" * 32
        + "\n💡 Kliknij odśwież (prawa góra), aby wygenerować kolejny dublet!"
    )
    page.update()

  fetch_scanner()

  # Widoki zakładek
  history_view = ft.Column(
      [
          ft.Row(
              [
                  goal_input,
                  ft.ElevatedButton(
                      "Przelicz",
                      on_click=lambda e: refresh_history(),
                      height=40,
                  ),
              ],
              alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
          ),
          summary_text,
          ft.Divider(),
          coupons_list,
      ],
      expand=True,
  )

  add_view = ft.Column(
      [
          ft.Text("➕ Dodaj Nowy Kupon", size=18, weight=ft.FontWeight.BOLD),
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
              bgcolor=ft.colors.GREEN,
              color=ft.colors.WHITE,
              width=300,
              on_click=save_coupon_click,
          ),
      ],
      spacing=10,
  )

  scanner_view = ft.Column(
      [
          ft.Row(
              [
                ft.Text("🔍 Skaner Dubletów Live", size=16, weight=ft.FontWeight.BOLD),
                ft.IconButton(ft.icons.REFRESH, on_click=fetch_scanner),
              ],
              alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
          ),
          scanner_box,
      ]
  )

  # Nowa zakładka z szybkimi linkami do analiz i statystyk sportowych/tenisowych
  def open_link(url):
    page.launch_url(url)

  analysis_view = ft.Column(
      [
          ft.Text("🔗 Narzędzia i Analizy Sportowe", size=18, weight=ft.FontWeight.BOLD),
          ft.Text("Szybki dostęp do statystyk, H2H i tabel:", size=12, color=ft.colors.GREY_400),
          ft.Divider(),
          ft.ElevatedButton(
              "📊 Flashscore (Wyniki na żywo i tabele)",
              icon=ft.icons.SPORTS_SOCCER,
              width=320,
              on_click=lambda e: open_link("https://www.flashscore.pl"),
          ),
          ft.ElevatedButton(
              "🎾 Tenis Explorer / Wyniki Tenisowe",
              icon=ft.icons.SPORTS_TENNIS,
              width=320,
              on_click=lambda e: open_link("https://www.flashtennis.pl"),
          ),
          ft.ElevatedButton(
              "📈 Sofascore (Szczegółowe statystyki & xG)",
              icon=ft.icons.ANALYTICS,
              width=320,
              on_click=lambda e: open_link("https://www.sofascore.com/pl/"),
          ),
          ft.ElevatedButton(
              "📉 OddsPortal (Historia i ruchy kursów)",
              icon=ft.icons.TRENDING_UP,
              width=320,
              on_click=lambda e: open_link("https://www.oddsportal.com"),
          ),
          ft.ElevatedButton(
              "⚽ WhoScored (Zaawansowana statystyka piłkarska)",
              icon=ft.icons.QUERY_STATS,
              width=320,
              on_click=lambda e: open_link("https://www.whoscored.com"),
          ),
      ],
      spacing=12,
      horizontal_alignment=ft.CrossAxisAlignment.CENTER,
  )

  body_container = ft.Container(content=history_view, expand=True, padding=12)

  def nav_change(e):
    go_to_tab(e.control.selected_index)

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
      body_container.content = analysis_view
    page.update()

  nav_bar = ft.NavigationBar(
      selected_index=0,
      on_change=nav_change,
      destinations=[
          ft.NavigationDestination(icon=ft.icons.BOOK, label="Dziennik"),
          ft.NavigationDestination(icon=ft.icons.ADD_CIRCLE_OUTLINE, label="Dodaj"),
          ft.NavigationDestination(icon=ft.icons.SEARCH, label="Skaner"),
          ft.NavigationDestination(icon=ft.icons.EXPLORE, label="Analiza"),
      ],
  )

  page.navigation_bar = nav_bar

  root_background = ft.Container(
      content=body_container,
      gradient=ft.LinearGradient(
          begin=ft.alignment.top_left,
          end=ft.alignment.bottom_right,
          colors=[
              "#0f172a",
              "#1e1b4b",
              "#090d16",
          ],
      ),
      expand=True,
  )

  page.add(root_background)
  refresh_history()


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 8550))
  ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port, host="0.0.0.0")
