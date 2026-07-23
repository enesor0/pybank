from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from uuid import UUID

from pybank.application.services import ApplicationError
from pybank.bootstrap import Application
from pybank.domain.errors import DomainError
from pybank.domain.models import AccountKind, EntryType, format_money


LIGHT = {"sage": "#c4c79b", "sand": "#d1cdb6", "navy": "#21324f", "blue": "#7286a8", "bg": "#f7f7f9", "card": "#ffffff", "text": "#21324f", "muted": "#64728a", "line": "#d1cdb6", "success": "#557461", "danger": "#a65c5c"}
DARK = {"sage": "#a9b478", "sand": "#aeb4c0", "navy": "#111827", "blue": "#7f94bb", "bg": "#0b1220", "card": "#172235", "text": "#f7f7f9", "muted": "#b5c0d3", "line": "#31405a", "success": "#8cc69e", "danger": "#f19a9a"}
COLORS = LIGHT.copy()


def apply_theme(dark: bool) -> None:
    COLORS.clear()
    COLORS.update(DARK if dark else LIGHT)


class PyBankDesktop(tk.Tk):
    def __init__(self, application: Application) -> None:
        super().__init__()
        self.application = application
        self.current_user = None
        self.current_account_id: UUID | None = None
        self.current_page = "overview"
        self.dark_mode = False
        self.title("PyBank | Güvenli Dijital Bankacılık")
        self.geometry("1180x780")
        self.minsize(980, 650)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self._configure_styles()
        self.show_auth()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview", background=COLORS["card"], fieldbackground=COLORS["card"], foreground=COLORS["text"], rowheight=39, borderwidth=0, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background=COLORS["line"], foreground=COLORS["text"], relief="flat", font=("Segoe UI Semibold", 10))
        style.map("Treeview", background=[("selected", COLORS["sage"])], foreground=[("selected", COLORS["navy"])])
        style.configure("TCombobox", padding=8, font=("Segoe UI", 10))

    def clear(self) -> None:
        for child in self.winfo_children():
            child.destroy()

    def show_auth(self) -> None:
        self.clear()
        self.configure(bg=COLORS["bg"])
        AuthScreen(self).pack(fill="both", expand=True)

    def login_success(self, user) -> None:
        self.current_user, self.current_account_id = user, None
        self.show_dashboard("overview")

    def show_dashboard(self, page: str | None = None) -> None:
        self.current_page = page or self.current_page
        self.clear()
        self.configure(bg=COLORS["bg"])
        self._configure_styles()
        DashboardScreen(self, self.current_page).pack(fill="both", expand=True)

    def toggle_theme(self) -> None:
        self.dark_mode = not self.dark_mode
        apply_theme(self.dark_mode)
        self.show_dashboard(self.current_page) if self.current_user else self.show_auth()

    def logout(self) -> None:
        self.current_user, self.current_account_id = None, None
        self.show_auth()

    def close(self) -> None:
        self.application.close()
        self.destroy()


class AuthScreen(tk.Frame):
    def __init__(self, app: PyBankDesktop) -> None:
        super().__init__(app, bg=COLORS["bg"])
        self.app, self.mode = app, "login"
        left = tk.Frame(self, bg=COLORS["navy"], width=450)
        left.pack(side="left", fill="both")
        left.pack_propagate(False)
        tk.Label(left, text="PYBANK", bg=COLORS["navy"], fg="white", font=("Segoe UI", 28, "bold")).pack(anchor="w", padx=58, pady=(100, 8))
        tk.Label(left, text="Bankacılığı sadeleştirdik.\nKontrol her zaman sende.", bg=COLORS["navy"], fg=COLORS["sage"], justify="left", font=("Segoe UI", 18)).pack(anchor="w", padx=58, pady=(0, 48))
        for text in ("✓  Güvenli parola koruması", "✓  Anlık ve atomik transfer", "✓  Kart ve fatura yönetimi"):
            tk.Label(left, text=text, bg=COLORS["navy"], fg="white", font=("Segoe UI", 11), pady=8).pack(anchor="w", padx=60)
        self.form = tk.Frame(self, bg=COLORS["bg"])
        self.form.pack(side="left", fill="both", expand=True, padx=88)
        self.render_form()

    def render_form(self) -> None:
        for child in self.form.winfo_children(): child.destroy()
        login = self.mode == "login"
        tk.Label(self.form, text="Hoş geldin" if login else "Hesabını oluştur", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 25, "bold")).pack(anchor="w", pady=(122, 8))
        tk.Label(self.form, text="Hesabına güvenle eriş." if login else "Dakikalar içinde dijital bankacılığa başla.", bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 30))
        self.name = self._field("AD SOYAD") if not login else None
        self.email, self.password = self._field("E-POSTA"), self._field("PAROLA", show="●")
        if not login: tk.Label(self.form, text="En az 8 karakter; harf ve rakam içermelidir.", bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 19))
        Button(self.form, "Giriş Yap" if login else "Hesabımı Oluştur", self.submit, primary=True).pack(fill="x")
        Button(self.form, "Henüz hesabın yok mu?  Kayıt ol" if login else "Zaten hesabın var mı?  Giriş yap", self.switch, text_button=True).pack(anchor="w", pady=(8, 0))
        self.email.focus_set()

    def _field(self, label: str, show: str | None = None) -> tk.Entry:
        tk.Label(self.form, text=label, bg=COLORS["bg"], fg=COLORS["blue"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
        entry = tk.Entry(self.form, bg=COLORS["card"], fg=COLORS["text"], insertbackground=COLORS["text"], relief="solid", bd=1, font=("Segoe UI", 11), show=show)
        entry.pack(fill="x", pady=(5, 20), ipady=8)
        return entry

    def switch(self) -> None:
        self.mode = "register" if self.mode == "login" else "login"
        self.render_form()

    def submit(self) -> None:
        try:
            user = self.app.application.authentication.login(self.email.get(), self.password.get()) if self.mode == "login" else self.app.application.authentication.register(self.name.get(), self.email.get(), self.password.get())
            if self.mode == "register": self.app.application.banking.open_account(user.id)
            self.app.login_success(user)
        except ApplicationError as error:
            messagebox.showerror("İşlem yapılamadı", str(error), parent=self.app)


class DashboardScreen(tk.Frame):
    def __init__(self, app: PyBankDesktop, page: str) -> None:
        super().__init__(app, bg=COLORS["bg"])
        self.app, self.page = app, page
        self._build_shell()
        self.render_page()

    def _build_shell(self) -> None:
        bar = tk.Frame(self, bg=COLORS["navy"], width=238)
        bar.pack(side="left", fill="y")
        bar.pack_propagate(False)
        tk.Label(bar, text="PYBANK", bg=COLORS["navy"], fg="white", font=("Segoe UI", 24, "bold")).pack(anchor="w", padx=28, pady=(34, 3))
        tk.Label(bar, text="Dijital bankacılık", bg=COLORS["navy"], fg=COLORS["sage"], font=("Segoe UI", 10)).pack(anchor="w", padx=30, pady=(0, 31))
        for key, icon, label in (("overview", "◈", "Genel Bakış"), ("transfer", "↔", "Para Transferi"), ("payments", "▣", "Ödemeler"), ("cards", "▤", "Kartlarım"), ("history", "◷", "İşlem Geçmişi"), ("settings", "⚙", "Ayarlar")):
            active = key == self.page
            Button(bar, f"{icon}   {label}", lambda value=key: self.go(value), primary=active, sidebar=True).pack(fill="x", padx=12, pady=2)
        tk.Frame(bar, bg=COLORS["line"], height=1).pack(fill="x", padx=26, pady=23)
        tk.Label(bar, text="Yerel simülasyon verileri\ncihazında saklanır.", bg=COLORS["navy"], fg=COLORS["sage"], justify="left", font=("Segoe UI", 10)).pack(anchor="w", padx=28)
        Button(bar, "⇥  Güvenli Çıkış", self.app.logout, sidebar=True).pack(anchor="w", padx=12, pady=(210, 0))
        self.content = tk.Frame(self, bg=COLORS["bg"])
        self.content.pack(side="left", fill="both", expand=True)

    def go(self, page: str) -> None:
        self.app.show_dashboard(page)

    def data(self):
        return self.app.application.banking.dashboard(self.app.current_user.id, self.app.current_account_id)

    def render_page(self) -> None:
        if self.page == "overview": self.overview()
        elif self.page == "transfer": self.transfer()
        elif self.page == "payments": self.payments()
        elif self.page == "cards": self.cards()
        elif self.page == "history": self.history()
        else: self.settings()

    def header(self, title: str, subtitle: str) -> None:
        top = tk.Frame(self.content, bg=COLORS["bg"])
        top.pack(fill="x", padx=42, pady=(28, 18))
        tk.Label(top, text=title, bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 23, "bold")).pack(anchor="w")
        tk.Label(top, text=subtitle, bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 0))

    def overview(self) -> None:
        data = self.data(); self.app.current_account_id = data.account.id
        self.header(f"Merhaba, {self.app.current_user.full_name.split()[0]}", "Finansal özetin ve hızlı işlemler burada.")
        selector = tk.Frame(self.content, bg=COLORS["bg"]); selector.pack(fill="x", padx=42, pady=(0, 10))
        tk.Label(selector, text="AKTİF HESAP", bg=COLORS["bg"], fg=COLORS["blue"], font=("Segoe UI", 9, "bold")).pack(side="left")
        picker = ttk.Combobox(selector, values=[f"{a.kind.value}  ·  {a.iban.value[-4:]}" for a in data.accounts], state="readonly", width=31)
        picker.current(next(i for i, account in enumerate(data.accounts) if account.id == data.account.id)); picker.pack(side="right")
        picker.bind("<<ComboboxSelected>>", lambda _event: self._select_account(data.accounts[picker.current()].id))
        card = tk.Frame(self.content, bg=COLORS["navy"], height=154); card.pack(fill="x", padx=42, pady=(0, 20)); card.pack_propagate(False)
        tk.Label(card, text="KULLANILABİLİR BAKİYE", bg=COLORS["navy"], fg=COLORS["sand"], font=("Segoe UI", 9, "bold")).place(x=25, y=23)
        tk.Label(card, text=format_money(data.account.balance), bg=COLORS["navy"], fg="white", font=("Segoe UI", 29, "bold")).place(x=25, y=46)
        tk.Label(card, text=data.account.iban.display, bg=COLORS["navy"], fg=COLORS["sage"], font=("Consolas", 10)).place(x=26, y=118)
        Button(card, "＋ Yeni Hesap", self.new_account, secondary=True).place(relx=.94, y=38, anchor="ne")
        Button(card, "IBAN Kopyala", lambda: self.copy(data.account.iban.value), secondary=True).place(relx=.94, y=92, anchor="ne")
        action = tk.Frame(self.content, bg=COLORS["bg"]); action.pack(fill="x", padx=42, pady=(0, 18))
        for label, command in (("＋ Para Yatır", lambda: self.cash_dialog("Para Yatır")), ("− Para Çek", lambda: self.cash_dialog("Para Çek")), ("↔ Transfer", lambda: self.go("transfer")), ("▣ Fatura Öde", lambda: self.go("payments"))):
            Button(action, label, command, secondary=True).pack(side="left", fill="x", expand=True, padx=4)
        self._recent(data, 5)

    def _recent(self, data, limit: int) -> None:
        block = tk.Frame(self.content, bg=COLORS["bg"]); block.pack(fill="both", expand=True, padx=42, pady=(0, 28))
        tk.Label(block, text="SON İŞLEMLER", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 9))
        tree = self.transaction_tree(block, data.transactions[:limit]); tree.pack(fill="both", expand=True)

    def transfer(self) -> None:
        data = self.data(); self.header("Para Transferi", "IBAN'a havale/EFT gönder; kayıtlı PyBank hesapları anında güncellenir.")
        form = self.form_card(); source, accounts = self.account_picker(form, data, "GÖNDEREN HESAP")
        iban = self.field(form, "ALICI IBAN")
        amount = self.field(form, "TUTAR (₺)")
        note = self.field(form, "AÇIKLAMA (OPSİYONEL)")
        Button(form, "Transferi Onayla", lambda: self._transfer(accounts, source.current(), iban.get(), amount.get(), note.get()), primary=True).pack(fill="x", pady=(7, 0))

    def _transfer(self, accounts, index, iban, amount, note) -> None:
        try:
            self.app.application.banking.transfer(self.app.current_user.id, accounts[index].id, iban, amount, note)
            self.app.current_account_id = accounts[index].id; self.success("Transfer başarıyla tamamlandı."); self.go("history")
        except (ApplicationError, DomainError) as error: self.fail(error)

    def payments(self) -> None:
        data = self.data(); self.header("Ödemeler", "Fatura ve düzenli ödeme simülasyonunu hesabından tamamla.")
        form = self.form_card(); source, accounts = self.account_picker(form, data, "ÖDEME HESABI")
        tk.Label(form, text="KURUM", bg=COLORS["card"], fg=COLORS["blue"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
        provider = ttk.Combobox(form, values=["Elektrik", "Su", "Doğal Gaz", "İnternet", "Cep Telefonu", "Kredi Kartı Borcu"], state="readonly")
        provider.current(0); provider.pack(fill="x", pady=(4, 13))
        subscriber = self.field(form, "ABONE / MÜŞTERİ NUMARASI")
        amount = self.field(form, "FATURA TUTARI (₺)")
        Button(form, "Ödemeyi Tamamla", lambda: self._pay_bill(accounts, source.current(), provider.get(), subscriber.get(), amount.get()), primary=True).pack(fill="x", pady=(7, 0))

    def _pay_bill(self, accounts, index, provider, subscriber, amount) -> None:
        try:
            self.app.application.banking.pay_bill(self.app.current_user.id, accounts[index].id, provider, subscriber, amount)
            self.app.current_account_id = accounts[index].id; self.success("Ödemen başarıyla tamamlandı."); self.go("history")
        except (ApplicationError, DomainError) as error: self.fail(error)

    def cards(self) -> None:
        cards = self.app.application.banking.cards_for(self.app.current_user.id)
        self.header("Kartlarım", "Sanal kartlarını görüntüle; kartı ve temassız kullanımı yönet.")
        canvas = tk.Frame(self.content, bg=COLORS["bg"]); canvas.pack(fill="both", expand=True, padx=42)
        if not cards:
            tk.Label(canvas, text="Henüz sanal kartın yok.", bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 12)).pack(anchor="w", pady=(18, 14))
            Button(canvas, "＋ Sanal Kart Oluştur", self.issue_card, primary=True).pack(anchor="w")
            return
        Button(canvas, "＋ Yeni Sanal Kart", self.issue_card, secondary=True).pack(anchor="e", pady=(0, 12))
        for card in cards:
            self.card_item(canvas, card)

    def card_item(self, parent, card) -> None:
        item = tk.Frame(parent, bg=COLORS["card"], highlightbackground=COLORS["line"], highlightthickness=1)
        item.pack(fill="x", pady=7)
        visual = tk.Frame(item, bg=COLORS["blue"], width=245, height=120); visual.pack(side="left", padx=14, pady=14); visual.pack_propagate(False)
        tk.Label(visual, text="PYBANK  •  SANAL", bg=COLORS["blue"], fg="white", font=("Segoe UI", 10, "bold")).place(x=16, y=15)
        tk.Label(visual, text=f"5353  ••••  ••••  {card.last_four}", bg=COLORS["blue"], fg="white", font=("Consolas", 11)).place(x=16, y=57)
        tk.Label(visual, text=f"SKT {card.expiry}", bg=COLORS["blue"], fg=COLORS["sage"], font=("Segoe UI", 9)).place(x=16, y=91)
        info = tk.Frame(item, bg=COLORS["card"]); info.pack(side="left", fill="both", expand=True, padx=4, pady=15)
        tk.Label(info, text=card.label, bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 13, "bold")).pack(anchor="w")
        status = "Donduruldu" if card.is_frozen else "Kullanıma açık"
        tk.Label(info, text=f"Durum: {status}   •   Temassız: {'Açık' if card.contactless_enabled else 'Kapalı'}", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 10)).pack(anchor="w", pady=(7, 9))
        Button(info, "Kartı Aç" if card.is_frozen else "Kartı Dondur", lambda ident=card.id: self.card_action(ident, "freeze"), secondary=True).pack(side="left", padx=(0, 7))
        Button(info, "Temassızı Kapat" if card.contactless_enabled else "Temassızı Aç", lambda ident=card.id: self.card_action(ident, "contactless"), secondary=True).pack(side="left")

    def issue_card(self) -> None:
        data = self.data()
        try:
            self.app.application.banking.issue_card(self.app.current_user.id, data.account.id)
            self.success("Sanal kartın oluşturuldu."); self.go("cards")
        except ApplicationError as error: self.fail(error)

    def card_action(self, card_id, action: str) -> None:
        if action == "freeze": self.app.application.banking.toggle_card_freeze(self.app.current_user.id, card_id)
        else: self.app.application.banking.toggle_contactless(self.app.current_user.id, card_id)
        self.go("cards")

    def history(self) -> None:
        data = self.data(); self.header("İşlem Geçmişi", "Seçili hesabının son 100 hareketini incele.")
        wrap = tk.Frame(self.content, bg=COLORS["bg"]); wrap.pack(fill="both", expand=True, padx=42, pady=(0, 30))
        self.transaction_tree(wrap, data.transactions).pack(fill="both", expand=True)

    def settings(self) -> None:
        self.header("Ayarlar", "Görünümünü ve yerel uygulama tercihlerini yönet.")
        card = self.form_card(); tk.Label(card, text="GÖRÜNÜM", bg=COLORS["card"], fg=COLORS["blue"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(card, text="Koyu tema", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(8, 1))
        tk.Label(card, text="Karanlık ortamlarda daha rahat bir görünüm kullan.", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 13))
        Button(card, "Açık Temaya Geç" if self.app.dark_mode else "Koyu Temaya Geç", self.app.toggle_theme, primary=True).pack(anchor="w")
        tk.Frame(card, bg=COLORS["line"], height=1).pack(fill="x", pady=22)
        tk.Label(card, text="GÜVENLİK", bg=COLORS["card"], fg=COLORS["blue"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(card, text="Parolalar PBKDF2 ile korunur; para ve kart verileri yalnızca bu bilgisayardaki SQLite veritabanında tutulur.", bg=COLORS["card"], fg=COLORS["muted"], justify="left", wraplength=560, font=("Segoe UI", 10)).pack(anchor="w", pady=(8, 0))

    def transaction_tree(self, parent, entries):
        tree = ttk.Treeview(parent, columns=("date", "type", "detail", "amount"), show="headings", selectmode="none")
        for key, text, width, anchor in (("date", "Tarih", 155, "w"), ("type", "İşlem", 155, "w"), ("detail", "Açıklama", 365, "w"), ("amount", "Tutar", 145, "e")):
            tree.heading(key, text=text, anchor=anchor); tree.column(key, width=width, anchor=anchor, stretch=key == "detail")
        tree.tag_configure("in", foreground=COLORS["success"]); tree.tag_configure("out", foreground=COLORS["danger"])
        for entry in entries:
            outgoing = entry.entry_type in (EntryType.WITHDRAWAL, EntryType.TRANSFER_OUT, EntryType.BILL_PAYMENT)
            detail = entry.description or (f"Karşı hesap: {entry.counterparty_iban}" if entry.counterparty_iban else "—")
            tree.insert("", "end", values=(entry.created_at.astimezone().strftime("%d.%m.%Y  %H:%M"), entry.entry_type.value, detail, ("−" if outgoing else "+") + format_money(entry.amount)), tags=("out" if outgoing else "in",))
        return tree

    def form_card(self):
        frame = tk.Frame(self.content, bg=COLORS["card"], highlightbackground=COLORS["line"], highlightthickness=1)
        frame.pack(fill="x", padx=42, pady=(0, 25)); frame.configure(padx=26, pady=24)
        return frame

    def field(self, parent, label: str) -> tk.Entry:
        tk.Label(parent, text=label, bg=COLORS["card"], fg=COLORS["blue"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
        entry = tk.Entry(parent, bg=COLORS["bg"], fg=COLORS["text"], insertbackground=COLORS["text"], relief="solid", bd=1, font=("Segoe UI", 11))
        entry.pack(fill="x", pady=(4, 13), ipady=7)
        return entry

    def account_picker(self, parent, data, label: str):
        tk.Label(parent, text=label, bg=COLORS["card"], fg=COLORS["blue"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
        picker = ttk.Combobox(parent, values=[f"{a.kind.value}  ·  {format_money(a.balance)}" for a in data.accounts], state="readonly")
        picker.current(next(i for i, account in enumerate(data.accounts) if account.id == data.account.id)); picker.pack(fill="x", pady=(4, 13))
        return picker, data.accounts

    def _select_account(self, account_id: UUID) -> None:
        self.app.current_account_id = account_id; self.go("overview")

    def copy(self, value: str) -> None:
        self.clipboard_clear(); self.clipboard_append(value); self.success("IBAN panoya kopyalandı.")

    def cash_dialog(self, title: str) -> None:
        dialog = tk.Toplevel(self.app); dialog.title(title); dialog.configure(bg=COLORS["card"]); dialog.geometry("390x310"); dialog.resizable(False, False); dialog.transient(self.app); dialog.grab_set()
        body = tk.Frame(dialog, bg=COLORS["card"]); body.pack(fill="both", expand=True, padx=28, pady=25)
        tk.Label(body, text=title, bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 18, "bold")).pack(anchor="w")
        amount = self.field(body, "TUTAR (₺)"); note = self.field(body, "AÇIKLAMA (OPSİYONEL)")
        def submit():
            try:
                data = self.data()
                action = self.app.application.banking.deposit if title == "Para Yatır" else self.app.application.banking.withdraw
                action(self.app.current_user.id, data.account.id, amount.get(), note.get())
                dialog.destroy(); self.success("İşlem başarıyla tamamlandı."); self.go("overview")
            except (ApplicationError, DomainError) as error: self.fail(error, dialog)
        Button(body, "İşlemi Onayla", submit, primary=True).pack(fill="x", pady=(3, 0))

    def new_account(self) -> None:
        dialog = tk.Toplevel(self.app); dialog.title("Yeni Hesap"); dialog.configure(bg=COLORS["card"]); dialog.geometry("390x250"); dialog.resizable(False, False); dialog.transient(self.app); dialog.grab_set()
        body = tk.Frame(dialog, bg=COLORS["card"]); body.pack(fill="both", expand=True, padx=28, pady=25)
        tk.Label(body, text="Yeni Hesap Aç", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(body, text="HESAP TÜRÜ", bg=COLORS["card"], fg=COLORS["blue"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(16, 3))
        kind = ttk.Combobox(body, values=[item.value for item in AccountKind], state="readonly"); kind.current(0); kind.pack(fill="x", pady=(0, 16))
        def create():
            account = self.app.application.banking.open_account(self.app.current_user.id, AccountKind(kind.get()))
            dialog.destroy(); self.success(f"{account.iban.display} IBAN'lı hesabın açıldı."); self.go("overview")
        Button(body, "Hesabı Oluştur", create, primary=True).pack(fill="x")

    def success(self, text: str) -> None: messagebox.showinfo("Başarılı", text, parent=self.app)
    def fail(self, error, parent=None) -> None: messagebox.showerror("İşlem yapılamadı", str(error), parent=parent or self.app)


class Button(tk.Button):
    def __init__(self, parent, text, command, primary=False, secondary=False, sidebar=False, text_button=False):
        if sidebar:
            bg, fg, active = (COLORS["blue"] if primary else COLORS["navy"]), "white", COLORS["blue"]
            super().__init__(parent, text=text, command=command, bg=bg, fg=fg, activebackground=active, activeforeground="white", relief="flat", cursor="hand2", anchor="w", padx=16, pady=11, font=("Segoe UI", 10))
        elif text_button:
            super().__init__(parent, text=text, command=command, bg=COLORS["bg"], fg=COLORS["blue"], activebackground=COLORS["bg"], relief="flat", cursor="hand2", font=("Segoe UI", 10), pady=7)
        else:
            bg, fg = (COLORS["navy"], "white") if primary else (COLORS["sand"], COLORS["navy"])
            if secondary: bg, fg = COLORS["blue"], "white"
            super().__init__(parent, text=text, command=command, bg=bg, fg=fg, activebackground=COLORS["sage"], activeforeground=COLORS["navy"], relief="flat", cursor="hand2", font=("Segoe UI Semibold", 10), padx=14, pady=10)
