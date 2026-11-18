from pathlib import Path


root = Path(SPECPATH).parent
gui = Analysis(
    [str(root / "scripts" / "gui_entry.py")],
    pathex=[str(root)],
    hiddenimports=["win32timezone"],
    excludes=["tkinter"],
)
service = Analysis(
    [str(root / "scripts" / "service_entry.py")],
    pathex=[str(root)],
    hiddenimports=["win32timezone"],
    excludes=["PySide6", "numpy", "cv2", "mss", "tkinter"],
)
gui_pyz = PYZ(gui.pure)
service_pyz = PYZ(service.pure)
gui_exe = EXE(
    gui_pyz, gui.scripts, [], exclude_binaries=True, name="Kidsroom",
    console=False, upx=False,
)
service_exe = EXE(
    service_pyz, service.scripts, [], exclude_binaries=True, name="KidsroomService",
    console=True, upx=False,
)
bundle = COLLECT(
    gui_exe, service_exe, gui.binaries, gui.datas, service.binaries, service.datas,
    name="Kidsroom", upx=False,
)
