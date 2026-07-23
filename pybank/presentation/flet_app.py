"""Flet tabanlı modern PyBank arayüzü; iş kuralları application katmanında kalır."""

from __future__ import annotations

import flet as ft

from pybank.application.services import ApplicationError
from pybank.bootstrap import Application
from pybank.domain.errors import DomainError
from pybank.domain.models import AccountKind, CardKind, EntryType, format_money


NAVY, BLUE, SAGE, SAND = "#21324f", "#7286a8", "#c4c79b", "#d1cdb6"
SURFACE, DARK_SURFACE, TEXT = "#F7F7F9", "#101827", "#21324F"


class PyBankFletApp:
    def __init__(self, page: ft.Page, application: Application) -> None:
        self.page, self.application = page, application
        self.user = None
        self.account_id = None
        self.active_page = 0
        self._configure_page()
        self.render_login()

    def _configure_page(self) -> None:
        self.page.title = "PyBank | Dijital Bankacılık"
        self.page.padding = 0
        # Masaüstü görünümü tasarım ölçülerinde sabit kalır; büyütme ve küçültme kapalıdır.
        self.page.window.width = 1280
        self.page.window.height = 960
        self.page.window.min_width = 1280
        self.page.window.max_width = 1280
        self.page.window.min_height = 960
        self.page.window.max_height = 960
        self.page.window.resizable = False
        self.page.window.maximizable = False
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = DARK_SURFACE

    @property
    def is_dark(self) -> bool:
        return self.page.theme_mode == ft.ThemeMode.DARK

    def color(self, name: str) -> str:
        palette = {
            "background": DARK_SURFACE if self.is_dark else SURFACE,
            "surface": "#1B2940" if self.is_dark else "#FFFFFF",
            "text": "#F7F7F9" if self.is_dark else TEXT,
            "muted": "#B5C0D3" if self.is_dark else "#64728A",
            "border": "#41516D" if self.is_dark else "#C8D0DB",
            "soft": "#22324E" if self.is_dark else "#E9EEF6",
        }
        return palette[name]

    def theme_toggle(self, _event=None) -> None:
        self.page.theme_mode = ft.ThemeMode.LIGHT if self.page.theme_mode == ft.ThemeMode.DARK else ft.ThemeMode.DARK
        self.page.bgcolor = SURFACE if self.page.theme_mode == ft.ThemeMode.LIGHT else DARK_SURFACE
        self.render_shell()

    def notice(self, text: str, error: bool = False) -> None:
        snack = ft.SnackBar(ft.Text(text, color="white"), bgcolor="#A65C5C" if error else "#557461", open=True)
        self.page.overlay.append(snack)
        self.page.update()

    def render_login(self) -> None:
        self.page.clean()
        name = ft.TextField(label="Ad soyad", visible=False, border_radius=10)
        email = ft.TextField(label="E-posta", border_radius=10, keyboard_type=ft.KeyboardType.EMAIL)
        password = ft.TextField(label="Parola", password=True, can_reveal_password=True, border_radius=10)
        mode = {"register": False}
        title = ft.Text("Hoş geldin", size=30, weight=ft.FontWeight.BOLD, color=self.color("text"))
        subtitle = ft.Text("PyBank hesabına güvenle eriş.", color="#C4C79B")
        submit = ft.FilledButton("Giriş Yap", icon=ft.Icons.LOGIN, width=340)
        switch = ft.TextButton("Henüz hesabın yok mu? Kayıt ol")

        def refresh_auth(_event=None):
            mode["register"] = not mode["register"]
            name.visible = mode["register"]
            title.value = "Hesabını oluştur" if mode["register"] else "Hoş geldin"
            subtitle.value = "Dakikalar içinde dijital bankacılığa başla." if mode["register"] else "PyBank hesabına güvenle eriş."
            submit.text = "Hesabımı Oluştur" if mode["register"] else "Giriş Yap"
            submit.icon = ft.Icons.PERSON_ADD if mode["register"] else ft.Icons.LOGIN
            switch.text = "Zaten hesabın var mı? Giriş yap" if mode["register"] else "Henüz hesabın yok mu? Kayıt ol"
            self.page.update()

        def authenticate(_event):
            try:
                if mode["register"]:
                    user = self.application.authentication.register(name.value or "", email.value or "", password.value or "")
                    self.application.banking.open_account(user.id)
                else:
                    user = self.application.authentication.login(email.value or "", password.value or "")
                self.user, self.account_id = user, None
                self.render_shell()
            except ApplicationError as exc:
                self.notice(str(exc), error=True)

        submit.on_click, switch.on_click = authenticate, refresh_auth
        brand = ft.Container(
            expand=4, bgcolor=NAVY, padding=ft.Padding.only(left=64, top=120),
            content=ft.Column([
                ft.Text("PYBANK", size=32, weight=ft.FontWeight.BOLD, color="white"),
                ft.Text("Dijital bankacılık", color=SAGE),
                ft.Container(height=40),
                ft.Text("Bankacılığı\nsadeleştirdik.", size=28, weight=ft.FontWeight.BOLD, color="white"),
                ft.Text("Kontrol her zaman sende.", size=16, color=SAGE),
                ft.Container(height=35),
                ft.Text("✓  Anlık transferler", color="white"),
                ft.Text("✓  Kart ve ödeme yönetimi", color="white"),
                ft.Text("✓  Koyu tema deneyimi", color="white"),
            ])
        )
        form = ft.Container(
            expand=6, padding=ft.Padding.only(left=90, top=150, right=90),
            content=ft.Column([title, subtitle, ft.Container(height=25), name, email, password, ft.Container(height=8), submit, switch], horizontal_alignment=ft.CrossAxisAlignment.START)
        )
        self.page.add(ft.Row([brand, form], expand=True, spacing=0))

    def render_shell(self) -> None:
        self.page.clean()
        self.page.overlay.clear()
        def nav_item(icon, selected_icon, label):
            return ft.NavigationRailDestination(
                ft.Icon(icon, color="#C8D3E6"),
                selected_icon=ft.Icon(selected_icon, color="white"),
                label=label,
            )

        rail = ft.NavigationRail(
            selected_index=self.active_page, extended=True, min_extended_width=230, bgcolor=NAVY,
            indicator_color=BLUE,
            selected_label_text_style=ft.TextStyle(color="white", weight=ft.FontWeight.BOLD),
            unselected_label_text_style=ft.TextStyle(color="#C8D3E6"),
            leading=ft.Container(padding=ft.Padding.only(left=25, top=25), content=ft.Column([
                ft.Row([ft.Container(width=31, height=31, border_radius=10, bgcolor=SAGE, alignment=ft.Alignment.CENTER, content=ft.Text("P", color=NAVY, weight=ft.FontWeight.BOLD)), ft.Text("PYBANK", size=24, weight=ft.FontWeight.BOLD, color="white")]),
                ft.Text("Dijital bankacılık", color=SAGE, size=12),
                ft.Container(height=8),
                ft.Text(self.user.full_name, color="#C8D3E6", size=11),
            ], spacing=3)),
            destinations=[
                nav_item(ft.Icons.DASHBOARD_OUTLINED, ft.Icons.DASHBOARD, "Genel Bakış"),
                nav_item(ft.Icons.SWAP_HORIZ, ft.Icons.SWAP_HORIZ, "Para Transferi"),
                nav_item(ft.Icons.RECEIPT_LONG_OUTLINED, ft.Icons.RECEIPT_LONG, "Ödemeler"),
                nav_item(ft.Icons.CREDIT_CARD_OUTLINED, ft.Icons.CREDIT_CARD, "Kartlarım"),
                nav_item(ft.Icons.HISTORY, ft.Icons.HISTORY, "İşlem Geçmişi"),
                nav_item(ft.Icons.SETTINGS_OUTLINED, ft.Icons.SETTINGS, "Ayarlar"),
            ],
            trailing=ft.Container(padding=20, content=ft.Column([
                ft.Text("Yerel simülasyon\ncihazında saklanır.", color=SAGE, size=11),
                ft.OutlinedButton("Çıkış", icon=ft.Icons.LOGOUT, on_click=self.logout,
                                  style=ft.ButtonStyle(color="#C8D3E6", side=ft.BorderSide(1, SAGE))),
            ], spacing=18)),
            on_change=self.change_page,
        )
        content = ft.Container(expand=True, padding=ft.Padding.symmetric(horizontal=42, vertical=30), content=self.build_page())
        self.page.add(ft.Row([rail, ft.VerticalDivider(width=1), content], expand=True, spacing=0))

    def change_page(self, event) -> None:
        self.active_page = event.control.selected_index
        self.render_shell()

    def logout(self, _event=None) -> None:
        self.user, self.account_id = None, None
        self.render_login()

    def dashboard(self):
        return self.application.banking.dashboard(self.user.id, self.account_id)

    def header(self, title: str, subtitle: str, action=None):
        controls = [ft.Column([ft.Text(title, size=27, weight=ft.FontWeight.BOLD, color=self.color("text")), ft.Text(subtitle, color=BLUE)])]
        right_controls = [ft.IconButton(ft.Icons.LIGHT_MODE if self.is_dark else ft.Icons.DARK_MODE, icon_color=self.color("text"), tooltip="Temayı değiştir", on_click=self.theme_toggle)]
        if action: right_controls.append(action)
        controls.append(ft.Row(right_controls, tight=True, spacing=6))
        return ft.Row(controls, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    def account_dropdown(self, data, label="HESAP"):
        selected = str(data.account.id)
        dropdown = ft.Dropdown(label=label, value=selected, options=[ft.DropdownOption(key=str(a.id), text=f"{a.kind.value} · {format_money(a.balance)}") for a in data.accounts], expand=True)
        return dropdown

    def build_page(self):
        builders = [self.overview, self.transfer, self.payments, self.cards, self.history, self.settings]
        return builders[self.active_page]()

    def overview(self):
        data = self.dashboard(); self.account_id = data.account.id
        dropdown = self.account_dropdown(data, "AKTİF HESAP")
        dropdown.on_select = lambda e: self.select_account(e.control.value)
        balance = ft.Container(
            gradient=ft.LinearGradient(colors=["#2D4671", "#1A2A45"]), border_radius=22, padding=30,
            content=ft.Row([
                ft.Column([ft.Row([ft.Container(padding=ft.Padding.symmetric(horizontal=10, vertical=5), border_radius=20, bgcolor="#FFFFFF1A", content=ft.Text(data.account.kind.value.upper(), color=SAGE, size=10, weight=ft.FontWeight.BOLD)), ft.Text("•  Hesabın güvende", color="#D4DCE8", size=11)]), ft.Container(height=6), ft.Text("KULLANILABİLİR BAKİYE", color=SAND, size=11, weight=ft.FontWeight.BOLD), ft.Text(format_money(data.account.balance), size=36, color="white", weight=ft.FontWeight.BOLD), ft.Text(data.account.iban.display, color=SAGE, font_family="Consolas")]),
                ft.Column([ft.FilledButton("＋ Yeni Hesap", on_click=self.open_account), ft.OutlinedButton("IBAN Kopyala", icon=ft.Icons.CONTENT_COPY, on_click=lambda e: self.copy_iban(data.account.iban.value), style=ft.ButtonStyle(color="white", side=ft.BorderSide(1, "#FFFFFF80")))], horizontal_alignment=ft.CrossAxisAlignment.END),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        )
        quick = ft.ResponsiveRow([
            self.quick("Para Yatır", ft.Icons.ADD_CIRCLE_OUTLINE, lambda e: self.cash_panel("deposit")),
            self.quick("Para Çek", ft.Icons.REMOVE_CIRCLE_OUTLINE, lambda e: self.cash_panel("withdraw")),
            self.quick("Transfer", ft.Icons.SWAP_HORIZ, lambda e: self.navigate(1)),
            self.quick("Fatura Öde", ft.Icons.RECEIPT_LONG, lambda e: self.navigate(2)),
        ])
        cards_count = len(self.application.banking.cards_for(self.user.id))
        metrics = ft.ResponsiveRow([
            self.metric("Toplam Hesap", str(len(data.accounts)), ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED),
            self.metric("Kartlarım", str(cards_count), ft.Icons.CREDIT_CARD_OUTLINED),
            self.metric("Son Hareket", str(len(data.transactions)), ft.Icons.TIMELINE_OUTLINED),
        ])
        return ft.Column([self.header(f"Merhaba, {self.user.full_name.split()[0]}", "Finansal özetin ve hızlı işlemler burada."), dropdown, balance, metrics, ft.Text("Hızlı İşlemler", size=16, weight=ft.FontWeight.BOLD, color=self.color("text")), quick, ft.Row([ft.Text("Son İşlemler", size=16, weight=ft.FontWeight.BOLD, color=self.color("text")), ft.TextButton("Tümünü Gör", on_click=lambda e: self.navigate(4))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), self.transaction_table(data.transactions[:5])], scroll=ft.ScrollMode.AUTO)

    def quick(self, label, icon, handler):
        return ft.Container(col={"sm": 6, "md": 3}, bgcolor=self.color("surface"), border=ft.Border.all(1, self.color("border")), border_radius=16, padding=16, on_click=handler, ink=True, content=ft.Column([ft.Container(width=38, height=38, border_radius=12, bgcolor=BLUE, alignment=ft.Alignment.CENTER, content=ft.Icon(icon, color="white", size=20)), ft.Container(height=3), ft.Text(label, color=self.color("text"), weight=ft.FontWeight.BOLD), ft.Text("İşlemi başlat", color=self.color("muted"), size=10)]))

    def metric(self, label, value, icon):
        return ft.Container(col={"sm": 4}, bgcolor=self.color("surface"), border=ft.Border.all(1, self.color("border")), border_radius=14, padding=14, content=ft.Row([ft.Container(width=34, height=34, border_radius=10, bgcolor=self.color("soft"), alignment=ft.Alignment.CENTER, content=ft.Icon(icon, color=BLUE, size=18)), ft.Column([ft.Text(value, size=18, weight=ft.FontWeight.BOLD, color=self.color("text")), ft.Text(label, size=10, color=self.color("muted"))], spacing=0)]))

    def navigate(self, index: int) -> None:
        self.active_page = index; self.render_shell()

    def select_account(self, account_id: str) -> None:
        self.account_id = __import__("uuid").UUID(account_id)
        self.render_shell()

    def transfer(self):
        data = self.dashboard(); sender = self.account_dropdown(data, "GÖNDEREN HESAP")
        iban, amount, note = ft.TextField(label="Alıcı IBAN", border_radius=10), ft.TextField(label="Tutar (₺)", border_radius=10), ft.TextField(label="Açıklama (opsiyonel)", border_radius=10)
        def send(_event):
            try:
                self.application.banking.transfer(self.user.id, __import__("uuid").UUID(sender.value), iban.value or "", amount.value or "", note.value or "")
                self.account_id = __import__("uuid").UUID(sender.value); self.notice("Transfer başarıyla tamamlandı."); self.navigate(4)
            except (ApplicationError, DomainError, ValueError) as exc: self.notice(str(exc), error=True)
        return ft.Column([self.header("Para Transferi", "IBAN'a havale/EFT gönder; tutarı virgülle de girebilirsin."), self.form_card([sender, iban, amount, note, ft.FilledButton("Transferi Onayla", icon=ft.Icons.SEND, on_click=send)])], scroll=ft.ScrollMode.AUTO)

    def payments(self):
        data = self.dashboard(); source = self.account_dropdown(data, "ÖDEME HESABI")
        provider = ft.Dropdown(label="Kurum", value="Elektrik", options=[ft.DropdownOption(text=x) for x in ["Elektrik", "Su", "Doğal Gaz", "İnternet", "Cep Telefonu", "Kredi Kartı Borcu"]])
        subscriber, amount = ft.TextField(label="Abone / müşteri numarası", border_radius=10), ft.TextField(label="Fatura tutarı (₺)", border_radius=10)
        def pay(_event):
            try:
                self.application.banking.pay_bill(self.user.id, __import__("uuid").UUID(source.value), provider.value or "", subscriber.value or "", amount.value or "")
                self.account_id = __import__("uuid").UUID(source.value); self.notice("Ödeme başarıyla tamamlandı."); self.navigate(4)
            except (ApplicationError, DomainError, ValueError) as exc: self.notice(str(exc), error=True)
        return ft.Column([self.header("Ödemeler", "Fatura ve düzenli ödeme simülasyonunu hesabından tamamla."), self.form_card([source, provider, subscriber, amount, ft.FilledButton("Ödemeyi Tamamla", icon=ft.Icons.PAYMENT, on_click=pay)])], scroll=ft.ScrollMode.AUTO)

    def cards(self):
        cards = self.application.banking.cards_for(self.user.id)
        actions = ft.Row([
            ft.OutlinedButton("Banka Kartı Oluştur", icon=ft.Icons.CREDIT_CARD, on_click=lambda e: self.create_card(CardKind.BANKA)),
            ft.OutlinedButton("Kredi Kartı Oluştur", icon=ft.Icons.CREDIT_SCORE, on_click=lambda e: self.create_card(CardKind.KREDI)),
            ft.FilledButton("Sanal Kart Oluştur", icon=ft.Icons.ADD_CARD, on_click=lambda e: self.create_card(CardKind.SANAL)),
        ], wrap=True)
        controls = [self.header("Kartlarım", "Banka ve sanal kartlarını güvenle yönet.", actions)]
        if not cards: controls.append(ft.Container(padding=30, bgcolor=self.color("surface"), border_radius=16, content=ft.Text("Henüz kartın yok. Banka veya sanal kart oluşturabilirsin.", color=self.color("muted"))))
        for card in cards:
            controls.append(self.card_tile(card))
        return ft.Column(controls, scroll=ft.ScrollMode.AUTO)

    def card_tile(self, card):
        def freeze(_event):
            self.application.banking.toggle_card_freeze(self.user.id, card.id); self.render_shell()
        def contactless(_event):
            self.application.banking.toggle_contactless(self.user.id, card.id); self.render_shell()
        def request_close(_event):
            self.request_card_close(card)
        visual_color = "#8B5CF6" if card.kind == CardKind.KREDI else (BLUE if card.kind == CardKind.SANAL else "#3E6D5A")
        visual = ft.Container(width=270, height=145, border_radius=18, padding=20, gradient=ft.LinearGradient(colors=[visual_color, "#21324F"]), content=ft.Column([
            ft.Text(f"PYBANK • {card.kind.value.upper()}", color="white", weight=ft.FontWeight.BOLD), ft.Container(expand=True), ft.Text(f"5353  ••••  ••••  {card.last_four}", color="white", font_family="Consolas"), ft.Text(f"SKT {card.expiry}", color=SAGE, size=11)
        ]))
        status = "Kapatma talimatı alındı" if card.is_closed else ("Donduruldu" if card.is_frozen else "Kullanıma açık")
        info = [ft.Text(card.label, size=18, weight=ft.FontWeight.BOLD), ft.Text(f"Durum: {status}")]
        if card.kind == CardKind.KREDI:
            info.extend([ft.Text(f"Kart limiti: {format_money(card.credit_limit)}", color=BLUE), ft.Text(f"Kullanılabilir limit: {format_money(card.available_credit)}", color="#8CC69E")])
        else:
            info.append(ft.Text(f"Temassız: {'Açık' if card.contactless_enabled else 'Kapalı'}", color=BLUE))
        if card.is_closed:
            info.append(ft.Text("Kart kalıcı olarak işleme kapatıldı.", color="#F19A9A", size=12))
        else:
            info.append(ft.Row([
                ft.OutlinedButton("Kartı Aç" if card.is_frozen else "Kartı Dondur", on_click=freeze),
                ft.OutlinedButton("Temassızı Kapat" if card.contactless_enabled else "Temassızı Aç", on_click=contactless),
                ft.TextButton("Kapatma Talimatı", icon=ft.Icons.BLOCK, on_click=request_close),
            ], wrap=True))
        details = ft.Column(info)
        return ft.Container(bgcolor=self.color("surface"), border=ft.Border.all(1, self.color("border")), border_radius=18, padding=18, content=ft.Row([visual, details], wrap=True, spacing=24))

    def create_card(self, kind: CardKind):
        data = self.dashboard()
        try:
            self.application.banking.issue_card(self.user.id, data.account.id, kind); self.notice(f"{kind.value} oluşturuldu."); self.render_shell()
        except ApplicationError as exc: self.notice(str(exc), error=True)

    def request_card_close(self, card) -> None:
        def confirm(_event):
            try:
                self.application.banking.close_card(self.user.id, card.id)
                self.close_dialog(dialog)
                self.notice("Kapatma talimatın alındı; kart işlemlere kapatıldı.")
                self.render_shell()
            except ApplicationError as exc:
                self.notice(str(exc), error=True)
        dialog = ft.AlertDialog(
            title=ft.Text("Kartı kapat"),
            content=ft.Text(f"{card.label} kalıcı olarak kapatılacak. Bu işlem geri alınamaz."),
            actions=[ft.TextButton("Vazgeç", on_click=lambda e: self.close_dialog(dialog)), ft.FilledButton("Talimatı Onayla", on_click=confirm)],
        )
        self.page.show_dialog(dialog)

    def history(self):
        data = self.dashboard()
        return ft.Column([self.header("İşlem Geçmişi", "Seçili hesabının son hareketleri."), self.transaction_table(data.transactions)], scroll=ft.ScrollMode.AUTO)

    def transaction_table(self, entries):
        rows = []
        for entry in entries:
            outgoing = entry.entry_type in (EntryType.WITHDRAWAL, EntryType.TRANSFER_OUT, EntryType.BILL_PAYMENT)
            detail = entry.description or (f"Karşı hesap: {entry.counterparty_iban}" if entry.counterparty_iban else "—")
            rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(entry.created_at.astimezone().strftime("%d.%m.%Y %H:%M"))), ft.DataCell(ft.Text(entry.entry_type.value)), ft.DataCell(ft.Text(detail)), ft.DataCell(ft.Text(("−" if outgoing else "+") + format_money(entry.amount), color="#F19A9A" if outgoing else "#8CC69E"))]))
        return ft.Container(bgcolor=self.color("surface"), border=ft.Border.all(1, self.color("border")), border_radius=14, padding=8, content=ft.DataTable(columns=[ft.DataColumn(ft.Text("Tarih", color="white")), ft.DataColumn(ft.Text("İşlem", color="white")), ft.DataColumn(ft.Text("Açıklama", color="white")), ft.DataColumn(ft.Text("Tutar", color="white"), numeric=True)], rows=rows, column_spacing=28, heading_row_color=BLUE))

    def settings(self):
        mode = "Açık" if self.page.theme_mode == ft.ThemeMode.LIGHT else "Koyu"
        data = self.dashboard()
        theme_switch = ft.Switch(label="Koyu tema", value=self.is_dark, active_color=BLUE, on_change=self.set_theme)
        profile = self.setting_card("Profil", "Hesap bilgilerin", [
            self.setting_row(ft.Icons.PERSON_OUTLINE, "Ad soyad", self.user.full_name),
            self.setting_row(ft.Icons.MAIL_OUTLINE, "E-posta", self.user.email),
            self.setting_row(ft.Icons.ACCOUNT_BALANCE_OUTLINED, "Aktif hesaplar", f"{len(data.accounts)} hesap"),
        ])
        appearance = self.setting_card("Görünüm", "Arayüz tercihlerin", [
            self.setting_row(ft.Icons.PALETTE_OUTLINED, "Tema", f"{mode} tema", theme_switch),
            self.setting_row(ft.Icons.DESKTOP_WINDOWS_OUTLINED, "Pencere düzeni", "1280 × 960 • Sabit boyut"),
            self.setting_row(ft.Icons.ANIMATION_OUTLINED, "Geçişler", "Yumuşak kart ve sayfa geçişleri"),
        ])
        security = self.setting_card("Güvenlik ve veri", "Yerel uygulama koruması", [
            self.setting_row(ft.Icons.LOCK_OUTLINED, "Parola güvenliği", "PBKDF2-HMAC-SHA256 ile korunuyor"),
            self.setting_row(ft.Icons.STORAGE, "Veri depolama", "Bu cihazdaki şifrelenmemiş yerel SQLite veritabanı"),
            self.setting_row(ft.Icons.CREDIT_CARD_OUTLINED, "Kartların", f"{len(self.application.banking.cards_for(self.user.id))} kart kayıtlı"),
        ])
        app_info = self.setting_card("Uygulama", "PyBank masaüstü simülasyonu", [
            self.setting_row(ft.Icons.INFO_OUTLINE, "Sürüm", "1.0.0 • Flet masaüstü arayüzü"),
            self.setting_row(ft.Icons.CLOUD_OFF_OUTLINED, "Bağlantı", "Gerçek banka veya ödeme ağına bağlı değil"),
            ft.Container(height=4),
            ft.OutlinedButton("Güvenli Çıkış", icon=ft.Icons.LOGOUT, on_click=self.logout),
        ])
        return ft.Column([self.header("Ayarlar", "Profilini, görünümünü ve uygulama tercihlerini yönet."), profile, appearance, security, app_info], scroll=ft.ScrollMode.AUTO, spacing=16)

    def set_theme(self, event) -> None:
        if bool(event.control.value) != self.is_dark:
            self.theme_toggle()

    def setting_card(self, title: str, subtitle: str, controls):
        return ft.Container(width=800, padding=22, border_radius=18, bgcolor=self.color("surface"), border=ft.Border.all(1, self.color("border")), content=ft.Column([
            ft.Text(title.upper(), color=BLUE, weight=ft.FontWeight.BOLD, size=11),
            ft.Text(subtitle, color=self.color("muted"), size=12),
            ft.Container(height=3),
            *controls,
        ], spacing=9))

    def setting_row(self, icon, label: str, value: str, trailing=None):
        right = trailing or ft.Text(value, color=self.color("muted"), size=12, text_align=ft.TextAlign.RIGHT)
        return ft.Container(padding=ft.Padding.symmetric(vertical=7), content=ft.Row([
            ft.Container(width=34, height=34, border_radius=10, bgcolor=self.color("soft"), alignment=ft.Alignment.CENTER, content=ft.Icon(icon, color=BLUE, size=18)),
            ft.Column([ft.Text(label, color=self.color("text"), weight=ft.FontWeight.W_500), ft.Text(value, color=self.color("muted"), size=11)], expand=True, spacing=1),
            right,
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER))

    def form_card(self, controls):
        return ft.Container(width=760, padding=28, border_radius=18, bgcolor=self.color("surface"), border=ft.Border.all(1, self.color("border")), content=ft.Column(controls, spacing=15))

    def cash_panel(self, action: str):
        data = self.dashboard(); amount, note = ft.TextField(label="Tutar (₺)", border_radius=10), ft.TextField(label="Açıklama (opsiyonel)", border_radius=10)
        def submit(_event):
            try:
                method = self.application.banking.deposit if action == "deposit" else self.application.banking.withdraw
                method(self.user.id, data.account.id, amount.value or "", note.value or "")
                self.notice("İşlem başarıyla tamamlandı."); self.render_shell()
            except (ApplicationError, DomainError) as exc: self.notice(str(exc), error=True)
        dialog = ft.AlertDialog(title=ft.Text("Para Yatır" if action == "deposit" else "Para Çek"), content=ft.Column([amount, note], tight=True), actions=[ft.TextButton("Vazgeç", on_click=lambda e: self.close_dialog(dialog)), ft.FilledButton("Onayla", on_click=submit)])
        self.page.show_dialog(dialog)

    def open_account(self, _event):
        kind = ft.Dropdown(label="Hesap türü", value=AccountKind.VADESIZ.value, options=[ft.DropdownOption(text=item.value) for item in AccountKind])
        def create(_click):
            account = self.application.banking.open_account(self.user.id, AccountKind(kind.value)); self.close_dialog(dialog); self.notice(f"{account.iban.display} IBAN'lı hesabın açıldı."); self.render_shell()
        dialog = ft.AlertDialog(title=ft.Text("Yeni Hesap Aç"), content=kind, actions=[ft.TextButton("Vazgeç", on_click=lambda e: self.close_dialog(dialog)), ft.FilledButton("Hesabı Oluştur", on_click=create)])
        self.page.show_dialog(dialog)

    def close_dialog(self, dialog):
        self.page.pop_dialog()

    def copy_iban(self, iban: str):
        self.page.clipboard.set(iban); self.notice("IBAN panoya kopyalandı.")


def run_flet(application: Application) -> None:
    ft.run(lambda page: PyBankFletApp(page, application))
