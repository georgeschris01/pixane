"""Fabrique python\\Chrypix.exe : une copie de pythonw.exe avec le nom « Chrypix » et l'icône de Chrypix,
pour que le Gestionnaire des tâches et le pare-feu montrent « Chrypix » et non « Python ».

Les ressources sont changées par Windows lui-même (BeginUpdateResource / UpdateResource), rien à télécharger.
Usage : python installateur/lanceur.py <pythonw.exe> <chrypix.ico> <Chrypix.exe> <version>
"""
from __future__ import annotations

import ctypes
import shutil
import struct
import sys
from ctypes import wintypes
from pathlib import Path

RT_ICON, RT_GROUP_ICON, RT_VERSION = 3, 14, 16
LOAD_LIBRARY_AS_DATAFILE = 0x2
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.BeginUpdateResourceW.restype = wintypes.HANDLE
k32.BeginUpdateResourceW.argtypes = [wintypes.LPCWSTR, wintypes.BOOL]
k32.UpdateResourceW.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, wintypes.WORD, ctypes.c_void_p,
                                wintypes.DWORD]
k32.EndUpdateResourceW.argtypes = [wintypes.HANDLE, wintypes.BOOL]
k32.LoadLibraryExW.restype = wintypes.HMODULE
k32.LoadLibraryExW.argtypes = [wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD]
k32.FreeLibrary.argtypes = [wintypes.HMODULE]
RAPPEL_NOM = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMODULE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
RAPPEL_LANGUE = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMODULE, ctypes.c_void_p, ctypes.c_void_p, wintypes.WORD,
                                   ctypes.c_void_p)
k32.EnumResourceNamesW.argtypes = [wintypes.HMODULE, ctypes.c_void_p, RAPPEL_NOM, ctypes.c_void_p]
k32.EnumResourceLanguagesW.argtypes = [wintypes.HMODULE, ctypes.c_void_p, ctypes.c_void_p, RAPPEL_LANGUE,
                                       ctypes.c_void_p]


def _ressources(exe: Path) -> list:
    """[(type, nom, langue)] des icônes et de la version déjà présentes (noms numériques seulement)."""
    trouve = []
    module = k32.LoadLibraryExW(str(exe), None, LOAD_LIBRARY_AS_DATAFILE)
    if not module:
        raise OSError(ctypes.get_last_error(), "LoadLibraryEx")
    try:
        for type_ in (RT_ICON, RT_GROUP_ICON, RT_VERSION):
            noms = []

            @RAPPEL_NOM
            def nom(_m, _t, n, _p):
                noms.append(n)
                return True
            k32.EnumResourceNamesW(module, type_, nom, None)
            for n in noms:
                if n is None or n >> 16:
                    raise RuntimeError("ressource à nom texte : non prévu")

                @RAPPEL_LANGUE
                def langue(_m, _t, _n, l, _p, n=n):
                    trouve.append((type_, n, l))
                    return True
                k32.EnumResourceLanguagesW(module, type_, n, langue, None)
    finally:
        k32.FreeLibrary(module)
    return trouve


def _bloc(cle: str, valeur: bytes = b"", texte: bool = False, enfants: bytes = b"") -> bytes:
    """Un bloc de VS_VERSIONINFO (longueur, longueur de la valeur, type, clé, valeur, enfants ; alignés sur 4)."""
    def aligner(b: bytes) -> bytes:
        return b + b"\0" * (-len(b) % 4)
    tete_cle = (cle + "\0").encode("utf-16-le")
    lg_valeur = len(valeur) // 2 if texte else len(valeur)
    corps = aligner(struct.pack("<HHH", 0, lg_valeur, 1 if texte or not valeur else 0) + tete_cle)
    corps = aligner(corps + valeur) + enfants
    return struct.pack("<H", len(corps)) + corps[2:]


def version_info(version: str) -> bytes:
    a, b, c = (int(x) for x in (version.split(".") + ["0", "0"])[:3])
    ms, ls = (a << 16) | b, c << 16
    fixe = struct.pack("<13I", 0xFEEF04BD, 0x00010000, ms, ls, ms, ls, 0x3F, 0, 0x40004, 1, 0, 0, 0)
    textes = {"CompanyName": "chrypox", "FileDescription": "Chrypix", "FileVersion": version,
              "InternalName": "Chrypix", "LegalCopyright": "chrypox", "OriginalFilename": "Chrypix.exe",
              "ProductName": "Chrypix", "ProductVersion": version}
    chaines = b"".join(_bloc(k, (v + "\0").encode("utf-16-le"), texte=True) for k, v in textes.items())
    table = _bloc("040904B0", enfants=chaines)
    sfi = _bloc("StringFileInfo", enfants=table)
    var = _bloc("Translation", struct.pack("<HH", 0x0409, 0x04B0))
    vfi = _bloc("VarFileInfo", enfants=var)
    return _bloc("VS_VERSION_INFO", fixe, enfants=sfi + vfi)


def icones(ico: Path) -> tuple[list[bytes], bytes]:
    """(images RT_ICON, répertoire RT_GROUP_ICON) tirés d'un fichier .ico."""
    data = ico.read_bytes()
    _, type_, n = struct.unpack_from("<HHH", data, 0)
    if type_ != 1:
        raise ValueError("pas un .ico")
    images, groupe = [], struct.pack("<HHH", 0, 1, n)
    for i in range(n):
        w, h, couleurs, res, plans, bits, taille, debut = struct.unpack_from("<BBBBHHII", data, 6 + 16 * i)
        images.append(data[debut:debut + taille])
        groupe += struct.pack("<BBBBHHIH", w, h, couleurs, res, plans, bits, taille, i + 1)
    return images, groupe


def _maj(h, type_, nom, langue, data: bytes | None):
    tampon = ctypes.create_string_buffer(data, len(data)) if data else None
    if not k32.UpdateResourceW(h, type_, nom, langue, tampon, len(data) if data else 0):
        raise OSError(ctypes.get_last_error(), f"UpdateResource {type_}/{nom}")


def fabriquer(pythonw: Path, ico: Path, sortie: Path, version: str) -> None:
    shutil.copyfile(pythonw, sortie)
    anciennes = _ressources(sortie)
    images, groupe = icones(ico)
    h = k32.BeginUpdateResourceW(str(sortie), False)
    if not h:
        raise OSError(ctypes.get_last_error(), "BeginUpdateResource")
    try:
        for type_, nom, langue in anciennes:
            _maj(h, type_, nom, langue, None)
        for i, img in enumerate(images, 1):
            _maj(h, RT_ICON, i, 0x0409, img)
        _maj(h, RT_GROUP_ICON, 1, 0x0409, groupe)
        _maj(h, RT_VERSION, 1, 0x0409, version_info(version))
    except BaseException:
        k32.EndUpdateResourceW(h, True)
        raise
    if not k32.EndUpdateResourceW(h, False):
        raise OSError(ctypes.get_last_error(), "EndUpdateResource")


if __name__ == "__main__":
    fabriquer(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4])
    print("ok :", sys.argv[3])
