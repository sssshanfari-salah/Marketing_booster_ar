# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

datas = [('C:/Users/ssssh/OneDrive/Documents/Marketing_booster_ar/starco_icon.ico', '.'), ('C:/Users/ssssh/OneDrive/Documents/Marketing_booster_ar/clients.json', '.'), ('C:/Users/ssssh/OneDrive/Documents/Marketing_booster_ar/users.json', '.'), ('C:/Users/ssssh/OneDrive/Documents/Marketing_booster_ar/guests.json', '.'), ('C:/Users/ssssh/OneDrive/Documents/Marketing_booster_ar/python_code/config/country_codes.json', '.'), ('C:/Users/ssssh/OneDrive/Documents/Marketing_booster_ar/python_code/config/Shops_Elect_meters.json', '.'), ('C:/Users/ssssh/OneDrive/Documents/Marketing_booster_ar/python_code/config/docs/documents.txt', '.'), ('C:/Users/ssssh/OneDrive/Documents/Marketing_booster_ar/python_code/config/translations.py', '.'), ('C:/Users/ssssh/OneDrive/Documents/Marketing_booster_ar/supporting_documents/starco_rent_contract_1.pdf', '.'), ('C:/Users/ssssh/OneDrive/Documents/Marketing_booster_ar/supporting_documents', '.'), ('C:/Users/ssssh/OneDrive/Documents/Marketing_booster_ar/starco icon', '.'), ('C:/Users/ssssh/OneDrive/Documents/Marketing_booster_ar/python_code', '.'), ('C:/Users/ssssh/OneDrive/Documents/Marketing_booster_ar/python_code/config', '.'), ('C:/Users/ssssh/OneDrive/Documents/Marketing_booster_ar/python_code/config/docs', '.'), ('C:/Users/ssssh/OneDrive/Documents/Marketing_booster_ar/Clients', '.'), ('C:/Users/ssssh/OneDrive/Documents/Marketing_booster_ar/application_outputs', '.'), ('C:/Users/ssssh/OneDrive/Documents/Marketing_booster_ar/application_outputs/clients_logs', '.'), ('C:/Users/ssssh/OneDrive/Documents/Marketing_booster_ar/application_outputs/tasks_logs', '.'), ('C:/Users/ssssh/OneDrive/Documents/Marketing_booster_ar/application_outputs/observation_logs', '.')]
binaries = []
hiddenimports = ['PIL', 'PIL.Image', 'PIL.ImageTk', 'PIL._imaging', 'PIL._imagingtk', 'arabic_reshaper', 'bidi', 'bidi.algorithm', 'config', 'config.translations', 'logic', 'logic.business_logic', 'logic.clients_management', 'logic.finance_manager', 'logic.models.contracts', 'logic.models.reservations', 'logic.models.transactions', 'logic.months', 'logic.progress_tracking', 'logic.save_contract', 'logic.shop_management', 'logic.shops_conversion_to_dic', 'logic.starco_finance', 'logic.sync_documents', 'logic.validations.Storage.client_storage', 'logic.validations.Storage.reports.client_payment_report', 'logic.validations.payment_rules', 'python_code', 'python_code.app.main', 'python_code.config.translations', 'python_code.logic.business_logic', 'python_code.logic.clients_management', 'python_code.logic.finance_manager', 'python_code.logic.models.contracts', 'python_code.logic.models.reservations', 'python_code.logic.models.transactions', 'python_code.logic.months', 'python_code.logic.progress_tracking', 'python_code.logic.save_contract', 'python_code.logic.shop_management', 'python_code.logic.shops_conversion_to_dic', 'python_code.logic.starco_finance', 'python_code.logic.sync_documents', 'python_code.logic.validations.Storage.client_storage', 'python_code.logic.validations.Storage.reports.client_payment_report', 'python_code.logic.validations.payment_rules', 'python_code.main', 'python_code.project_paths', 'python_code.ui.client_actions', 'python_code.ui.client_transactions_window', 'python_code.ui.dashboard', 'python_code.ui.main_app', 'python_code.ui.reservation_contract', 'python_code.ui.session', 'python_code.ui.shared', 'python_code.ui.treeview_positioning', 'python_code.ui.utils', 'tkinter', 'tkinter.colorchooser', 'tkinter.commondialog', 'tkinter.constants', 'tkinter.filedialog', 'tkinter.font', 'tkinter.messagebox', 'tkinter.simpledialog', 'tkinter.ttk', 'ui', 'ui.client_actions', 'ui.client_transactions_window', 'ui.dashboard', 'ui.main_app', 'ui.reservation_contract', 'ui.session', 'ui.shared', 'ui.treeview_positioning', 'ui.utils', 'webbrowser']
hiddenimports += collect_submodules('logic')
hiddenimports += collect_submodules('ui')
hiddenimports += collect_submodules('config')
hiddenimports += collect_submodules('python_code')
tmp_ret = collect_all('tkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('bidi')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('arabic_reshaper')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PIL')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['C:/Users/ssssh/OneDrive/Documents/Marketing_booster_ar/python_code/app/main.py'],
    pathex=['C:/Users/ssssh/OneDrive/Documents/Marketing_booster_ar/python_code', 'C:/Users/ssssh/OneDrive/Documents/Marketing_booster_ar'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='marketing_booster_ar',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:/Users/ssssh/OneDrive/Documents/Marketing_booster_ar/starco_icon.ico'],
)
