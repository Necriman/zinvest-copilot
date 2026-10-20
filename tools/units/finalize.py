"""Turn out/uNN.json into the files the backend imports:
backend/learning/content/units/uNN.json, one per unit, with the Russian
figures of unit 1 (rendered without Cyrillic glyphs in the source PDF)
replaced by tables in Russian, and the unused Russian PNGs removed."""
import json
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEST = REPO / "backend" / "learning" / "content" / "units"
DEST.mkdir(parents=True, exist_ok=True)

RU_FIGURES = {
    # Figure 1.2: the three pillars of finance.
    "fig-2.png": (
        "<table><tbody>"
        "<tr><th><p>Личные финансы</p><p>Физические лица и семьи</p></th>"
        "<th><p>Корпоративные финансы</p><p>Компании и корпорации</p></th>"
        "<th><p>Государственные финансы</p><p>Государство и учреждения</p></th></tr>"
        "<tr><td><p>Бюджет и сбережения</p></td><td><p>Капитальное бюджетирование</p></td><td><p>Государственный бюджет</p></td></tr>"
        "<tr><td><p>Ипотека и кредиты</p></td><td><p>Структура капитала</p></td><td><p>Налоговая политика</p></td></tr>"
        "<tr><td><p>Пенсионное планирование</p></td><td><p>Оборотный капитал</p></td><td><p>Управление госдолгом</p></td></tr>"
        "<tr><td><p>Страхование и налоги</p></td><td><p>Дивидендная политика</p></td><td><p>Пенсионные системы</p></td></tr>"
        "<tr><td><p>Инвестиционный портфель</p></td><td><p>Слияния и поглощения</p></td><td><p>Финансирование инфраструктуры</p></td></tr>"
        "</tbody></table>"
    ),
    # Figure 1.4: economics vs accounting vs finance.
    "fig-4.png": (
        "<table><tbody>"
        "<tr><th><p>Экономика</p></th><th><p>Бухгалтерия</p></th><th><p>Финансы</p></th></tr>"
        "<tr><td><p>Изучает, КАК общество распределяет ограниченные ресурсы</p></td>"
        "<td><p>Фиксирует и отражает, ЧТО произошло с деньгами</p></td>"
        "<td><p>Решает, ЧТО ДЕЛАТЬ с деньгами, чтобы создать ценность</p></td></tr>"
        "<tr><td><p>Смотрит в прошлое и будущее</p></td><td><p>Смотрит в прошлое</p></td><td><p>Смотрит в будущее</p></td></tr>"
        "<tr><td><p>Результат: теории и политика</p></td><td><p>Результат: финансовая отчётность</p></td><td><p>Результат: инвестиционные решения</p></td></tr>"
        "</tbody></table>"
    ),
}


def fix_ru_figures(html):
    def swap(m):
        return RU_FIGURES.get(m.group(1), "")
    return re.sub(r'<img src="/units/u01/ru/(fig-\d+\.png)" alt="">', swap, html)


for path in sorted((HERE / "out").glob("u*.json")):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data["unit"] == 1 and "ru" in data["langs"]:
        ru = data["langs"]["ru"]
        for lesson in ru["lessons"]:
            lesson["html"] = fix_ru_figures(lesson["html"])
    for lang in data["langs"].values():
        lang.pop("body_size", None)
        lang.pop("body_x", None)
    (DEST / path.name).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(path.name, {k: len(v["lessons"]) for k, v in data["langs"].items()})

shutil.rmtree(REPO / "frontend" / "public" / "units" / "u01" / "ru", ignore_errors=True)
print("ru figures removed")
