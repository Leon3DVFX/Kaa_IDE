from importlib import resources

path = resources.files('Kaa_IDE.UI.Icons')
pn = str(path.joinpath('x_normal.png')).replace('\\', '/')
ph = str(path.joinpath('x_hovered.png')).replace('\\', '/')
pa = str(path.joinpath('x_activate.png')).replace('\\', '/')

css = f'''
QTabBar {{
    font-family: JetBrains Mono;
    border: none;
}}

/* Вкладка */
QTabBar::tab {{
    background: #503E3E42;
    color: #D0D0D0;
    padding: 4px 2px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    min-width: 80px;
}}

/* Выбранная вкладка */
QTabBar::tab:selected {{
    background: #3E3E42;
    color: #C6D7EEF9;
    font-weight: 700;
}}

/* Невыбранная вкладка при наведении */
QTabBar::tab:hover:!selected {{
    background: #46464A;
    color: #C9C9C9
}}
/* Невыбранная вкладка */
QTabBar::tab:!selected {{
    color: #99C9C9C9;
}}

/* Кнопка закрытия на вкладке */
QTabBar::close-button {{
    image: url({pn});  /* путь к твоей иконке */
    width: 16px;                         /* ширина кнопки */
    height: 16px;                        /* высота кнопки */
    subcontrol-origin: padding;           /* отступ внутри вкладки */
    subcontrol-position: right;           /* справа */
    margin: 0px 2px;                      /* отступ сверху/снизу = 0, справа = 2px */
}}

/* При наведении */
QTabBar::close-button:hover {{
    image: url({ph});  /* иконка при hover */
}}

/* При нажатии */
QTabBar::close-button:pressed {{
    image: url({pa}); /* иконка при нажатии */
}}
'''


if __name__ == '__main__':
    print(css)