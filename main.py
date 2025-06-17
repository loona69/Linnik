import tkinter as tk
from tkinter import ttk, messagebox
import csv
import os
import sys
import sqlite3
from datetime import datetime, timedelta
from calculate import calculate_discount, calculate_products

#для получения файлов .py, а также для запуска бд
def get_script_directory():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

SCRIPT_DIRECTORY = get_script_directory()
DB_FILE = os.path.join(SCRIPT_DIRECTORY, "db.db")

#функция для создания базы данных
def create_database(db_file):
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        print("База данных создана успешно")

        # поставщики
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suppliers (
                supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                inn TEXT
            )
        """)

        # партнеры
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS partners (
                 partner_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT NOT NULL UNIQUE,
                 partner_type TEXT NOT NULL,
                 rating INTEGER NOT NULL CHECK(rating >= 0),
                 address TEXT,
                 director_name TEXT,
                 phone TEXT,
                 email TEXT,
                 inn TEXT UNIQUE,
                 logo TEXT,
                 sales_locations TEXT
            )
        """)

        # менеджеры
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS managers (
                 manager_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT NOT NULL,
                 email TEXT NOT NULL UNIQUE,
                 password TEXT NOT NULL
            )      
        """)

        #кадры
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                  employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  birth_date TEXT,
                  passport TEXT,
                  bank_details TEXT,
                  family_status TEXT,
                  health_status TEXT
            )           
        """)

        #продукты
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                  product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  article TEXT NOT NULL,
                  type TEXT NOT NULL,
                  name TEXT NOT NULL,
                  description TEXT,
                  image TEXT,
                  min_partner_price REAL NOT NULL,
                  package_length REAL,
                  package_width REAL,
                  package_height REAL,
                  weight_no_package REAL,
                  weight_with_package REAL,
                  certificate TEXT,
                  standard_number TEXT,
                  production_time INTEGER,
                  cost_price REAL,
                  workshop_number INTEGER,
                  labor_count INTEGER,
                  product_type_id INTEGER NOT NULL,
                  param1 REAL NOT NULL CHECK(param1 > 0),
                  param2 REAL NOT NULL CHECK(param2 > 0)
            )
        """)

        #материалы
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS materials (
                  material_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  type TEXT NOT NULL,
                  name TEXT NOT NULL,
                  supplier_id INTEGER,
                  package_quantity INTEGER,
                  unit TEXT,
                  description TEXT,
                  image TEXT,
                  cost REAL NOT NULL,
                  stock_quantity INTEGER NOT NULL,
                  min_quantity INTEGER,
                  FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id) ON DELETE SET NULL
            )
        """)

        #продажи
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                  sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  partner_id INTEGER NOT NULL,
                  product_id INTEGER NOT NULL,
                  quantity INTEGER NOT NULL CHECK(quantity >0),
                  sale_date TEXT NOT NULL,
                  FOREIGN KEY (partner_id) REFERENCES partners(partner_id) ON DELETE RESTRICT,
                  FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT
             )
        """)

        #заявки
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                  order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  partner_id INTEGER NOT NULL,
                  manager_id INTEGER NOT NULL,
                  product_id INTEGER NOT NULL,
                  quantity INTEGER NOT NULL CHECK(quantity > 0),
                  cost REAL NOT NULL,
                  production_date TEXT,
                  status TEXT NOT NULL,
                  created_date TEXT NOT NULL,
                  prepayment_date TEXT,
                  completion_date TEXT,
                  FOREIGN KEY (partner_id) REFERENCES partners(partner_id) ON DELETE RESTRICT,
                  FOREIGN KEY (manager_id) REFERENCES managers(manager_id) ON DELETE RESTRICT,
                  FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT
            )
        """)

        #складские перемещения
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS warehouse_movements (
                  movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  material_id INTEGER,
                  product_id INTEGER,
                  quantity INTEGER NOT NULL,
                  movement_type TEXT NOT NULL,
                  date TEXT NOT NULL,
                  FOREIGN KEY (material_id) REFERENCES materials(material_id) ON DELETE RESTRICT,
                  FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT
            )
        """)

        #логи
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS access_logs (
                  log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  employee_id INTEGER NOT NULL,
                  door_id INTEGER NOT NULL,
                  timestamp TEXT NOT NULL,
                  FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE RESTRICT
            )
        """)

        #создание тестовых данных для входа
        cursor.execute("""
             INSERT OR IGNORE INTO managers (name, email, password)
             VALUES (?, ?, ?)
        """, ('Test Manager', 'test@manager.com', 'password123'))

        conn.commit()
        print('Таблицы созданы')
    except sqlite3.Error as e:
        print(f"SQLite ошибка создания таблиц: {str(e)}")
        raise
    except Exception as e:
        print(f"Неизвестная ошибка {str(e)}")
    finally:
        conn.close()
        print('База данных закрыла соединение')


#функция для импорта данных из csv файлов(перенес все из xlsx файлов, колонки по английски назвал)
def import_csv_data(db_file):
    import_warnings = []
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        print("Foreign keys enabled for import")

        partner_headers = ['name', 'partner_type', 'rating', 'address', 'director_name', 'phone', 'email', 'inn', 'logo', 'sales_locations']
        product_headers = ['article', 'type', 'name', 'description', 'image', 'min_partner_price', 'package_length', 'package_width', 'package_height', 'weight_no_package', 'weight_with_package', 'certificate', 'standard_number', 'production_time', 'cost_price', 'workshop_number', 'labor_count', 'product_type_id', 'param1', 'param2']
        sales_headers = ['partner_id', 'product_id', 'quantity', 'sale_date']
        material_headers = ['type', 'name', 'supplier_id', 'package_quantity', 'unit', 'description', 'image', 'cost', 'stock_quantity', 'min_quantity']
        supplier_headers = ['type', 'name', 'inn']

        partners_inserted = 0
        products_inserted = 0
        sales_inserted = 0
        materials_inserted = 0
        suppliers_inserted = 0

        cursor.execute("SELECT supplier_id FROM suppliers")
        valid_supplier_ids = {row[0] for row in cursor.fetchall()}
        print(f"Valid supplier_ids: {valid_supplier_ids}")

        def validate_headers(file_path, expected_headers):
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                return reader.fieldnames, all(h in reader.fieldnames for h in expected_headers)

        suppliers_path = os.path.join(SCRIPT_DIRECTORY, 'suppliers.csv')
        if os.path.exists(suppliers_path):
            try:
                fieldnames, headers_valid = validate_headers(suppliers_path, supplier_headers)
                if not headers_valid:
                    raise ValueError(f"Неправильные заголовки в suppliers.csv. Expected: {supplier_headers}, Found: {fieldnames}")
                with open(suppliers_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            cursor.execute('''
                                INSERT OR IGNORE INTO suppliers (type, name, inn)
                                VALUES (?, ?, ?)
                            ''', (row['type'], row['name'], row['inn'] or None))
                            if cursor.rowcount > 0:
                                suppliers_inserted += 1
                        except (ValueError, sqlite3.Error) as e:
                            continue
            except Exception as e:
                import_warnings.append(f"Ошибка импорта suppliers.csv: {str(e)}")
        cursor.execute("SELECT supplier_id FROM suppliers")
        valid_supplier_ids = {row[0] for row in cursor.fetchall()}

        materials_path = os.path.join(SCRIPT_DIRECTORY, 'materials.csv')
        if os.path.exists(materials_path):
            try:
                fieldnames, headers_valid = validate_headers(materials_path, material_headers)
                if not headers_valid:
                    raise ValueError(f"Incorrect headers in materials.csv. Expected: {material_headers}, Found: {fieldnames}")
                with open(materials_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            supplier_id = int(row['supplier_id']) if row['supplier_id'] else None
                            if supplier_id and supplier_id not in valid_supplier_ids:
                                print(f"Skipping material row with invalid supplier_id={supplier_id}: {row}")
                                continue
                            cursor.execute('''
                                INSERT OR IGNORE INTO materials (type, name, supplier_id, package_quantity, unit, description, image, cost, stock_quantity, min_quantity)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (row['type'], row['name'], supplier_id, int(row['package_quantity']) if row['package_quantity'] else None,
                                  row['unit'] or None, row['description'] or None, row['image'] or None, float(row['cost']),
                                  int(row['stock_quantity']), int(row['min_quantity']) if row['min_quantity'] else None))
                            if cursor.rowcount > 0:
                                materials_inserted += 1
                        except (ValueError, sqlite3.Error) as e:
                            continue
            except Exception as e:
                import_warnings.append(f"Ошибка испорта materials.csv: {str(e)}")
                print(f"Предупреждение: {str(e)}")
        else:
            import_warnings.append(f"materials.csv not found at {materials_path}")
        partners_path = os.path.join(SCRIPT_DIRECTORY, 'partners.csv')
        if os.path.exists(partners_path):
            try:
                fieldnames, headers_valid = validate_headers(partners_path, partner_headers)
                if not headers_valid:
                    raise ValueError(f"Incorrect headers in partners.csv. Expected: {partner_headers}, Found: {fieldnames}")
                with open(partners_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            cursor.execute('SELECT partner_id FROM partners WHERE name = ? OR (inn IS NOT NULL AND inn = ?)',
                                         (row['name'], row['inn'] or None))
                            if cursor.fetchone():
                                print(f"Skipping duplicate partner: name={row['name']}, inn={row['inn']}")
                                continue
                            cursor.execute('''
                                INSERT INTO partners (name, partner_type, rating, address, director_name, phone, email, inn, logo, sales_locations)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (row['name'], row['partner_type'], int(row['rating']), row['address'] or None,
                                  row['director_name'] or None, row['phone'] or None, row['email'] or None,
                                  row['inn'] or None, row['logo'] or None, row['sales_locations'] or None))
                            partners_inserted += 1
                        except (ValueError, sqlite3.Error) as e:
                            print(f"Error importing row in partners.csv: {row}, Error: {str(e)}")
                            continue
                print(f"Imported {partners_inserted} rows from partners.csv")
            except Exception as e:
                import_warnings.append(f"Ошибка импорта partners.csv: {str(e)}")
        else:
            import_warnings.append(f"partners.csv not found at {partners_path}")

        cursor.execute("SELECT partner_id FROM partners")
        valid_partner_ids = {row[0] for row in cursor.fetchall()}

        products_path = os.path.join(SCRIPT_DIRECTORY, 'products.csv')
        if os.path.exists(products_path):
            try:
                fieldnames, headers_valid = validate_headers(products_path, product_headers)
                if not headers_valid:
                    raise ValueError(f"Неправильные заголовки в products.csv. Expected: {product_headers}, Found: {fieldnames}")
                with open(products_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            cursor.execute('''
                                INSERT OR IGNORE INTO products (article, type, name, description, image, min_partner_price, package_length, package_width, package_height, weight_no_package, weight_with_package, certificate, standard_number, production_time, cost_price, workshop_number, labor_count, product_type_id, param1, param2)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (row['article'], row['type'], row['name'], row['description'] or None, row['image'] or None,
                                  float(row['min_partner_price']), float(row['package_length']) if row['package_length'] else None,
                                  float(row['package_width']) if row['package_width'] else None, float(row['package_height']) if row['package_height'] else None,
                                  float(row['weight_no_package']) if row['weight_no_package'] else None, float(row['weight_with_package']) if row['weight_with_package'] else None,
                                  row['certificate'] or None, row['standard_number'] or None, int(row['production_time']) if row['production_time'] else None,
                                  float(row['cost_price']) if row['cost_price'] else None, int(row['workshop_number']) if row['workshop_number'] else None,
                                  int(row['labor_count']) if row['labor_count'] else None, int(row['product_type_id']),
                                  float(row['param1']), float(row['param2'])))
                            if cursor.rowcount > 0:
                                products_inserted += 1
                        except (ValueError, sqlite3.Error) as e:
                            print(f"Ошибка импота строк products.csv: {row}, Error: {str(e)}")
                            continue
                print(f"Imported {products_inserted} rows from products.csv")
            except Exception as e:
                import_warnings.append(f"Ошибка импорта в products.csv: {str(e)}")
        else:
            import_warnings.append(f"products.csv not found at {products_path}")

        cursor.execute("SELECT product_id FROM products")
        valid_product_ids = {row[0] for row in cursor.fetchall()}

        sales_path = os.path.join(SCRIPT_DIRECTORY, 'sales.csv')
        if os.path.exists(sales_path):
            try:
                fieldnames, headers_valid = validate_headers(sales_path, sales_headers)
                if not headers_valid:
                    raise ValueError(f"Неправильные заголовки в sales.csv. Expected: {sales_headers}, Found: {fieldnames}")
                with open(sales_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            partner_id = int(row['partner_id'])
                            product_id = int(row['product_id'])
                            if partner_id not in valid_partner_ids:
                                print(f"Skipping sale row with invalid partner_id={partner_id}: {row}")
                                continue
                            if product_id not in valid_product_ids:
                                print(f"Skipping sale row with invalid product_id={product_id}: {row}")
                                continue
                            cursor.execute('''
                                INSERT OR IGNORE INTO sales (partner_id, product_id, quantity, sale_date)
                                VALUES (?, ?, ?, ?)
                            ''', (partner_id, product_id, int(row['quantity']), row['sale_date']))
                            if cursor.rowcount > 0:
                                sales_inserted += 1
                        except (ValueError, sqlite3.Error) as e:
                            print(f"Error importing row in sales.csv: {row}, Error: {str(e)}")
                            continue
            except Exception as e:
                import_warnings.append(f"Failed to import sales.csv: {str(e)}")
        else:
            import_warnings.append(f"sales.csv not found at {sales_path}")
        conn.commit()
        return import_warnings
    except sqlite3.Error as e:
        print(f"SQLite error importing CSV data: {str(e)}")
        raise
    finally:
        conn.close()
        print("Database connection closed for import")

#инициализация базы данных
def initialize_db(db_file):
    try:
        print(f'Инициализация с базой данных: {db_file}')
        create_database(db_file)
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
        tables = [row[0] for row in cursor.fetchall()]
        print(f'Существующие таблицы {tables}')
        cursor.execute("SELECT COUNT(*) FROM partners")
        partners_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM products")
        products_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM sales")
        sales_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM materials")
        materials_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM suppliers")
        suppliers_count = cursor.fetchone()[0]
        conn.close()

        import_warnings = []
        if partners_count == 0 or products_count == 0 or sales_count == 0 or materials_count == 0 or suppliers_count == 0:
            import_warnings = import_csv_data(db_file)
        else:
            return import_warnings

    except sqlite3.Error as e:
        print(f"SQLite ошибка базы данных: {str(e)}")
        messagebox.showerror("Ошибка", f"Не удалось инициализировать базу данных: {str(e)}")
        raise
    except Exception as e:
        print(f"Неизвестная ошибка инициализации: {str(e)}")
        messagebox.showerror("Ошибка", f"Неожиданная ошибка: {str(e)}")
        raise

#проверка создания таблиц
def table_exists(db_file, table_name):
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    except sqlite3.Error as e:
        return False

#окно авторизации
class LoginDialog(tk.Toplevel):
    def __init__(self, parent, db_file, callback):
        super().__init__(parent)
        self.parent = parent
        self.db_file = db_file
        self.callback = callback
        self.iconbitmap('logo.ico')
        self.title('Авторизация менеджера')
        self.geometry('300x150')
        self.transient(parent)
        self.grab_set()
        self.configure(bg='#FFFFFF')
        self.init_ui()

        #инициализация интерфейса
    def init_ui(self):
        frame = ttk.Frame(self, padding="10")
        frame.grid(column=0, row=0, sticky="nsew")

        ttk.Label(frame, text="Почта:").grid(row=0, column=0, sticky="w", pady=2)
        self.email_input = ttk.Entry(frame)
        self.email_input.grid(row=0, column=1, sticky="ew", pady=2)
        self.email_input.insert(0, "test@manager.com")

        ttk.Label(frame, text="Пароль:").grid(row=1, column=0, sticky="w", pady=2)
        self.password_input = ttk.Entry(frame, show="*")
        self.password_input.grid(row=1, column=1, sticky="ew", pady=2)
        self.password_input.insert(0, "password123")

        ttk.Button(frame, text="Войти", command=self.login).grid(row=2, column=0, columnspan=2, pady=10)

        frame.columnconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

    def login(self):
        try:
            email = self.email_input.get().strip()
            password = self.password_input.get().strip()
            if not table_exists(self.db_file, 'managers'):
                messagebox.showerror("Ошибка", "Таблица 'managers' не существует.", parent=self)
                return
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT manager_id, name FROM managers WHERE email = ? AND password = ?", (email, password))
            manager = cursor.fetchone()
            conn.close()
            if manager:
                self.callback(manager[0], manager[1])
                self.destroy()
            else:
                messagebox.showerror("Ошибка", "Неверная почта или пароль.", parent=self)
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Ошибка входа: {str(e)}", parent=self)

#окно добавления/редактирования партнера
class PartnerDialog(tk.Toplevel):
    def __init__(self, parent, db_file, manager_id, partner_id=None):
        super().__init__(parent)
        self.parent = parent
        self.db_file = db_file
        self.iconbitmap('logo.ico')
        self.manager_id = manager_id
        self.partner_id = partner_id
        self.title("Редактировать партнера" if partner_id else "Добавить партнера")
        self.geometry("400x400")
        self.transient(parent)
        self.configure(bg='#FF0000')
        self.grab_set()
        self.init_ui()
        if partner_id:
            self.load_partner_data()

    def init_ui(self):
        frame = ttk.Frame(self, padding="10")
        frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frame, text="Наименование:").grid(row=0, column=0, sticky="w", pady=2)
        self.name_input = ttk.Entry(frame)
        self.name_input.grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="Тип партнера:").grid(row=1, column=0, sticky="w", pady=2)
        self.type_input = ttk.Combobox(frame, values=["Дистрибьютор", "Розничный"], state="readonly")
        self.type_input.grid(row=1, column=1, sticky="ew", pady=2)
        self.type_input.set("Дистрибьютор")

        ttk.Label(frame, text="Рейтинг:").grid(row=2, column=0, sticky="w", pady=2)
        self.rating_input = ttk.Entry(frame)
        self.rating_input.grid(row=2, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="Адрес:").grid(row=3, column=0, sticky="w", pady=2)
        self.address_input = ttk.Entry(frame)
        self.address_input.grid(row=3, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="ФИО директора:").grid(row=4, column=0, sticky="w", pady=2)
        self.director_input = ttk.Entry(frame)
        self.director_input.grid(row=4, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="Телефон:").grid(row=5, column=0, sticky="w", pady=2)
        self.phone_input = ttk.Entry(frame)
        self.phone_input.grid(row=5, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="Email:").grid(row=6, column=0, sticky="w", pady=2)
        self.email_input = ttk.Entry(frame)
        self.email_input.grid(row=6, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="ИНН:").grid(row=7, column=0, sticky="w", pady=2)
        self.inn_input = ttk.Entry(frame)
        self.inn_input.grid(row=7, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="Логотип (путь):").grid(row=8, column=0, sticky="w", pady=2)
        self.logo_input = ttk.Entry(frame)
        self.logo_input.grid(row=8, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="Места продаж:").grid(row=9, column=0, sticky="w", pady=2)
        self.sales_locations_input = ttk.Entry(frame)
        self.sales_locations_input.grid(row=9, column=1, sticky="ew", pady=2)

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=10, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Сохранить", command=self.save_partner).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Отмена", command=self.destroy).grid(row=0, column=1, padx=5)

        frame.columnconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

    def load_partner_data(self):
        try:
            if not table_exists(self.db_file, 'partners'):
                messagebox.showerror("Ошибка", "Таблица 'partners' не существует.", parent=self)
                return
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM partners WHERE partner_id = ?', (self.partner_id,))
            partner = cursor.fetchone()
            conn.close()

            if partner:
                self.name_input.insert(0, partner[1])
                self.type_input.set(partner[2])
                self.rating_input.insert(0, str(partner[3]))
                self.address_input.insert(0, partner[4] or "")
                self.director_input.insert(0, partner[5] or "")
                self.phone_input.insert(0, partner[6] or "")
                self.email_input.insert(0, partner[7] or "")
                self.inn_input.insert(0, partner[8] or "")
                self.logo_input.insert(0, partner[9] or "")
                self.sales_locations_input.insert(0, partner[10] or "")
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить данные партнера: {str(e)}", parent=self)

    def save_partner(self):
        try:
            if not table_exists(self.db_file, 'partners'):
                messagebox.showerror("Ошибка", "Таблица 'partners' не существует.", parent=self)
                return
            name = self.name_input.get().strip()
            partner_type = self.type_input.get()
            rating = int(self.rating_input.get().strip())
            address = self.address_input.get().strip() or None
            director = self.director_input.get().strip() or None
            phone = self.phone_input.get().strip() or None
            email = self.email_input.get().strip() or None
            inn = self.inn_input.get().strip() or None
            logo = self.logo_input.get().strip() or None
            sales_locations = self.sales_locations_input.get().strip() or None

            if not name or rating < 0:
                messagebox.showwarning("Ошибка", "Заполните обязательные поля: наименование и рейтинг (неотрицательный).", parent=self)
                return

            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute('SELECT partner_id FROM partners WHERE (name = ? AND partner_id != ?) OR (inn IS NOT NULL AND inn = ? AND partner_id != ?)',
                           (name, self.partner_id or 0, inn or '', self.partner_id or 0))
            if cursor.fetchone():
                messagebox.showwarning("Ошибка", "Партнер с таким наименованием или ИНН уже существует.", parent=self)
                conn.close()
                return

            if self.partner_id:
                cursor.execute('''
                    UPDATE partners SET name = ?, partner_type = ?, rating = ?, address = ?, director_name = ?, phone = ?, email = ?, inn = ?, logo = ?, sales_locations = ?
                    WHERE partner_id = ?
                ''', (name, partner_type, rating, address, director, phone, email, inn, logo, sales_locations, self.partner_id))
            else:
                cursor.execute('''
                    INSERT INTO partners (name, partner_type, rating, address, director_name, phone, email, inn, logo, sales_locations)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, partner_type, rating, address, director, phone, email, inn, logo, sales_locations))
            conn.commit()
            conn.close()
            self.parent.load_partners()
            self.destroy()
        except ValueError:
            messagebox.showwarning("Ошибка", "Рейтинг должен быть целым неотрицательным числом.", parent=self)
        except sqlite3.Error as e:
            print(f"Ошибка сохранения партнера: {str(e)}")
            messagebox.showerror("Ошибка", f"Ошибка сохранения: {str(e)}", parent=self)

#окно истории продаж
class SalesDialog(tk.Toplevel):
     def __init__(self, parent, db_file, partner_id):
         super().__init__(parent)
         self.parent = parent
         self.db_file = db_file
         self.partner_id = partner_id
         self.iconbitmap('logo.ico')
         self.title("История продаж")
         self.configure(bg='#FFFFFF')
         self.geometry("600x450")
         self.transient(parent)
         self.grab_set()
         self.init_ui()

     def init_ui(self):
         frame = ttk.Frame(self, padding="10")
         frame.grid(row=0, column=0, sticky="nsew")

         self.sales_table = ttk.Treeview(frame, columns=("Продукция", "Количество", "Дата продажи", "Скидка"), show="headings")
         self.sales_table.heading("Продукция", text="Продукция")
         self.sales_table.heading("Количество", text="Количество")
         self.sales_table.heading("Дата продажи", text="Дата продажи")
         self.sales_table.heading("Скидка", text="Скидка")
         self.sales_table.column("Продукция", width=200)
         self.sales_table.column("Количество", width=100)
         self.sales_table.column("Дата продажи", width=150)
         self.sales_table.column("Скидка", width=100)
         self.sales_table.grid(row=0, column=0, sticky="nsew")

         scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.sales_table.yview)
         self.sales_table.configure(yscrollcommand=scrollbar.set)
         scrollbar.grid(row=0, column=1, sticky="ns")

         ttk.Button(frame, text="Назад", command=self.destroy).grid(row=1, column=0, pady=10)

         frame.columnconfigure(0, weight=1)
         frame.rowconfigure(0, weight=1)
         self.columnconfigure(0, weight=1)
         self.rowconfigure(0, weight=1)

         self.load_sales_data()

     def load_sales_data(self):
         try:
             if not table_exists(self.db_file, 'sales') or not table_exists(self.db_file, 'products'):
                 messagebox.showerror("Ошибка", "Таблицы 'sales' или 'products' не существуют.", parent=self)
                 return
             conn = sqlite3.connect(self.db_file)
             cursor = conn.cursor()

             cursor.execute("SELECT name FROM partners WHERE partner_id = ?", (self.partner_id,))
             partner = cursor.fetchone()
             if not partner:
                 messagebox.showerror("Ошибка", f"Партнер с ID {self.partner_id} не найден.", parent=self)
                 conn.close()
                 return
             cursor.execute('SELECT SUM(quantity) FROM sales WHERE partner_id = ?', (self.partner_id,))
             total_quantity = cursor.fetchone()[0] or 0
             discount = calculate_discount(total_quantity)

             cursor.execute('''
                 SELECT p.name, s.quantity, s.sale_date
                 FROM sales s
                 JOIN products p ON s.product_id = p.product_id
                 WHERE s.partner_id = ?
             ''', (self.partner_id,))
             sales = cursor.fetchall()
             conn.close()
             for sale in sales:
                 self.sales_table.insert("", "end", values=(sale[0], sale[1], sale[2], f"{discount}%"))
             if not sales:
                 messagebox.showinfo("Информация", "Нет данных о продажах для этого партнера.", parent=self)
         except sqlite3.Error as e:
             print(f"Ошибка загрузки данных из истории продаж: {str(e)}")
             messagebox.showerror("Ошибка", f"Не удалось загрузить историю продаж: {str(e)}", parent=self)

#окно для создании заявки
class OrderDialog(tk.Toplevel):
    def __init__(self, parent, db_file, manager_id, partner_id=None):
        super().__init__(parent)
        self.parent = parent
        self.db_file = db_file
        self.manager_id = manager_id
        self.partner_id = partner_id
        self.iconbitmap('logo.ico')
        self.title('Создать заявку')
        self.geometry('500x350')
        self.transient(parent)
        self.grab_set()
        self.init_ui()

    def init_ui(self):
        frame = ttk.Frame(self, padding="10")
        frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frame, text="Партнер:").grid(row=0, column=0, sticky="w", pady=2)
        self.partner_combobox = ttk.Combobox(frame, state="readonly")
        self.partner_combobox.grid(row=0, column=1, sticky="ew", pady=2)
        self.load_partners()

        ttk.Label(frame, text="Продукт:").grid(row=1, column=0, sticky="w", pady=2)
        self.product_combobox = ttk.Combobox(frame, state="readonly")
        self.product_combobox.grid(row=1, column=1, sticky="ew", pady=2)
        self.load_products()

        ttk.Label(frame, text="Количество:").grid(row=2, column=0, sticky="w", pady=2)
        self.quantity_input = ttk.Entry(frame)
        self.quantity_input.grid(row=2, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="Стоимость:").grid(row=3, column=0, sticky="w", pady=2)
        self.cost_input = ttk.Entry(frame)
        self.cost_input.grid(row=3, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="Дата производства:").grid(row=4, column=0, sticky="w", pady=2)
        self.production_date_input = ttk.Entry(frame)
        self.production_date_input.grid(row=4, column=1, sticky="ew", pady=2)
        self.production_date_input.insert(0, (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"))

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Создать", command=self.create_order).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Отмена", command=self.destroy).grid(row=0, column=1, padx=5)

        frame.columnconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        if self.partner_id:
            self.partner_combobox.set(self.get_partner_name(self.partner_id))

    def load_partners(self):
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT partner_id, name FROM partners")
            partners = cursor.fetchall()
            conn.close()
            self.partner_combobox['values'] = [f"{p[1]} (ID: {p[0]})" for p in partners]
            self.partner_map = {f"{p[1]} (ID: {p[0]})": p[0] for p in partners}
        except sqlite3.Error as e:
            print(f"Ошибка загрузки партнеров: {str(e)}")

    def load_products(self):
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT product_id, name FROM products")
            products = cursor.fetchall()
            conn.close()
            self.product_combobox['values'] = [f"{p[1]} (ID: {p[0]})" for p in products]
            self.product_map = {f"{p[1]} (ID: {p[0]})": p[0] for p in products}
        except sqlite3.Error as e:
            print(f"Ошибка загрузки продуктов: {str(e)}")

    def get_partner_name(self, partner_id):
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM partners WHERE partner_id = ?", (partner_id,))
            name = cursor.fetchone()[0]
            conn.close()
            return f"{name} (ID: {partner_id})"
        except sqlite3.Error:
            return ""

    def create_order(self):
        try:
            partner_text = self.partner_combobox.get()
            product_text = self.product_combobox.get()
            quantity = int(self.quantity_input.get().strip())
            cost = float(self.cost_input.get().strip())
            production_date = self.production_date_input.get().strip()

            if not partner_text or not product_text or quantity <= 0 or cost <= 0 or not production_date:
                messagebox.showwarning("Ошибка", "Заполните все поля корректно.", parent=self)
                return

            partner_id = self.partner_map.get(partner_text)
            product_id = self.product_map.get(product_text)
            if not partner_id or not product_id:
                messagebox.showerror("Ошибка", "Выберите корректного партнера и продукт.", parent=self)
                return

            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO orders (partner_id, manager_id, product_id, quantity, cost, production_date, status, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (partner_id, self.manager_id, product_id, quantity, cost, production_date, "created", datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            conn.close()
            self.parent.load_orders()
            self.destroy()
        except ValueError:
            messagebox.showwarning("Ошибка", "Количество и стоимость должны быть положительными числами.", parent=self)
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Ошибка создания заявки: {str(e)}", parent=self)

#окно для добавления/редактирования сотрудника
class EmployeeDialog(tk.Toplevel):
    def __init__(self, parent, db_file, employee_id=None):
        super().__init__(parent)
        self.parent = parent
        self.db_file = db_file
        self.employee_id = employee_id
        self.iconbitmap('logo.ico')
        self.configure(bg='#FFFFFF')
        self.title("Редактировать сотрудника" if employee_id else "Добавить сотрудника")
        self.geometry("400x300")
        self.transient(parent)
        self.grab_set()
        self.init_ui()
        if employee_id:
            self.load_employee_data()


    def init_ui(self):
            frame = ttk.Frame(self, padding="10")
            frame.grid(row=0, column=0, sticky="nsew")

            ttk.Label(frame, text="ФИО:").grid(row=0, column=0, sticky="w", pady=2)
            self.name_input = ttk.Entry(frame)
            self.name_input.grid(row=0, column=1, sticky="ew", pady=2)

            ttk.Label(frame, text="Дата рождения:").grid(row=1, column=0, sticky="w", pady=2)
            self.birth_date_input = ttk.Entry(frame)
            self.birth_date_input.grid(row=1, column=1, sticky="ew", pady=2)

            ttk.Label(frame, text="Паспорт:").grid(row=2, column=0, sticky="w", pady=2)
            self.passport_input = ttk.Entry(frame)
            self.passport_input.grid(row=2, column=1, sticky="ew", pady=2)

            ttk.Label(frame, text="Банковские реквизиты:").grid(row=3, column=0, sticky="w", pady=2)
            self.bank_input = ttk.Entry(frame)
            self.bank_input.grid(row=3, column=1, sticky="ew", pady=2)

            ttk.Label(frame, text="Семейное положение:").grid(row=4, column=0, sticky="w", pady=2)
            self.family_input = ttk.Entry(frame)
            self.family_input.grid(row=4, column=1, sticky="ew", pady=2)

            ttk.Label(frame, text="Состояние здоровья:").grid(row=5, column=0, sticky="w", pady=2)
            self.health_input = ttk.Entry(frame)
            self.health_input.grid(row=5, column=1, sticky="ew", pady=2)

            button_frame = ttk.Frame(frame)
            button_frame.grid(row=6, column=0, columnspan=2, pady=10)
            ttk.Button(button_frame, text="Сохранить", command=self.save_employee).grid(row=0, column=0, padx=5)
            ttk.Button(button_frame, text="Отмена", command=self.destroy).grid(row=0, column=1, padx=5)

            frame.columnconfigure(1, weight=1)
            self.columnconfigure(0, weight=1)
            self.rowconfigure(0, weight=1)

    #загрузка данных сотрудника в базу данных
    def load_employee_data(self):
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM employees WHERE employee_id = ?', (self.employee_id,))
            employee = cursor.fetchone()
            conn.close()

            if employee:
                self.name_input.insert(0, employee[1])
                self.birth_date_input.insert(0, employee[2] or "")
                self.passport_input.insert(0, employee[3] or "")
                self.bank_input.insert(0, employee[4] or "")
                self.family_input.insert(0, employee[5] or "")
                self.health_input.insert(0, employee[6] or "")
        except sqlite3.Error as e:
            messagebox.showerror('Ошибка', f'Не удалось загрузить данные сотрудника: {str(e)}', parent=self)

    #сохранение данных сотрудника
    def save_employee(self):
        try:
            name = self.name_input.get().strip()
            birth_date = self.birth_date_input.get().strip() or None
            passport = self.passport_input.get().strip() or None
            bank = self.bank_input.get().strip() or None
            family = self.family_input.get().strip() or None
            health = self.health_input.get().strip() or None

            if not name:
                messagebox.showwarning("Ошибка", "ФИО обязательно для заполнения.", parent=self)
                return

            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            if self.employee_id:
                cursor.execute('''
                    UPDATE employees SET name = ?, birth_date = ?, passport = ?, bank_details = ?, family_status = ?, health_status = ?
                    WHERE employee_id = ?
                ''', (name, birth_date, passport, bank, family, health, self.employee_id))
            else:
                cursor.execute('''
                    INSERT INTO employees (name, birth_date, passport, bank_details, family_status, health_status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name, birth_date, passport, bank, family, health))
            conn.commit()
            conn.close()
            self.parent.load_employees()
            self.destroy()
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Ошибка сохранения сотрудника: {str(e)}", parent=self)

#Журнал доступа
class AccessLogDialog(tk.Toplevel):
    def __init__(self, parent, db_file, main_app_ref):
        """
        :param parent: родительское окно
        :param db_file: путь к файлу БД
        :param main_app_ref: ссылка на главное приложение
        """
        super().__init__(parent)
        self.parent = parent
        self.db_file = db_file
        self.main_app = main_app_ref
        self.iconbitmap('logo.ico')
        self.configure(bg='#FFFFFF')
        self.title('Журнал доступа')
        self.geometry("600x400")
        self.transient(parent)
        self.grab_set()
        self.init_ui()

    def init_ui(self):
        frame = ttk.Frame(self, padding="10")
        frame.grid(row=0, column=0, sticky="nsew")

        # Создаем таблицу с колонками
        columns = ("ID", "Сотрудник", "Дверь", "Время")
        self.access_table = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        # Настраиваем заголовки
        for col in columns:
            self.access_table.heading(col, text=col)
            self.access_table.column(col, width=100)

        self.access_table.grid(row=0, column=0, sticky="nsew")

        # Скроллбар
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.access_table.yview)
        self.access_table.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Фрейм для кнопок
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=1, column=0, pady=10, sticky='ew')
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        # Кнопки действий
        ttk.Button(
            button_frame,
            text="Добавить запись",
            command=self.add_access_log
        ).grid(row=0, column=0, padx=5, sticky='ew')

        ttk.Button(
            button_frame,
            text="Удалить запись",
            command=self.delete_selected_log,
            style="Danger.TButton"
        ).grid(row=0, column=1, padx=5, sticky='ew')

        # Кнопка закрытия
        ttk.Button(
            frame,
            text="Назад",
            command=self.close_dialog
        ).grid(row=2, column=0, pady=5, sticky='ew')

        # Настройка растягивания
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Стиль для кнопки удаления
        style = ttk.Style()
        style.configure("Danger.TButton", foreground="red")

        # Загрузка данных
        self.load_access_logs()

    def close_dialog(self):
        """Закрывает диалог и обновляет главное окно"""
        self.destroy()
        self.main_app.load_access_logs()  # Обновляем главное окно

    def load_access_logs(self):
        """Загружает данные журнала доступа из БД"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Выбираем данные с JOIN для получения имени сотрудника
            cursor.execute('''
                           SELECT a.log_id,
                                  e.name,
                                  a.door_id,
                                  a.timestamp
                           FROM access_logs a
                                    JOIN employees e ON a.employee_id = e.employee_id
                           ORDER BY a.timestamp DESC
                           ''')

            logs = cursor.fetchall()
            conn.close()

            # Очищаем таблицу перед загрузкой новых данных
            for item in self.access_table.get_children():
                self.access_table.delete(item)

            # Заполняем таблицу данными
            for log in logs:
                self.access_table.insert("", "end", values=log)

        except sqlite3.Error as e:
            messagebox.showerror(
                "Ошибка базы данных",
                f"Не удалось загрузить журнал доступа:\n{str(e)}",
                parent=self
            )

    def delete_selected_log(self):
        """Удаляет выбранную запись из журнала"""
        selected_item = self.access_table.selection()

        if not selected_item:
            messagebox.showwarning(
                "Выбор записи",
                "Пожалуйста, выберите запись для удаления",
                parent=self
            )
            return

        # Получаем ID записи
        log_id = self.access_table.item(selected_item, "values")[0]

        # Подтверждение удаления
        if not messagebox.askyesno(
                "Подтверждение удаления",
                "Вы уверены, что хотите удалить эту запись?",
                parent=self
        ):
            return

        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Выполняем удаление
            cursor.execute("DELETE FROM access_logs WHERE log_id = ?", (log_id,))
            conn.commit()
            conn.close()

            # Обновляем таблицу в диалоге
            self.load_access_logs()

            # Обновляем главное окно
            self.main_app.load_access_logs()

            messagebox.showinfo(
                "Успешное удаление",
                "Запись успешно удалена из журнала",
                parent=self
            )

        except sqlite3.Error as e:
            messagebox.showerror(
                "Ошибка удаления",
                f"Не удалось удалить запись:\n{str(e)}",
                parent=self
            )

    def add_access_log(self):
        """Добавляет тестовую запись доступа"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Получаем первого сотрудника
            cursor.execute("SELECT employee_id FROM employees LIMIT 1")
            employee = cursor.fetchone()

            if not employee:
                messagebox.showwarning(
                    "Нет сотрудников",
                    "В системе нет зарегистрированных сотрудников",
                    parent=self
                )
                return

            employee_id = employee[0]
            door_id = 1
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Вставляем новую запись
            cursor.execute('''
                           INSERT INTO access_logs (employee_id, door_id, timestamp)
                           VALUES (?, ?, ?)
                           ''', (employee_id, door_id, timestamp))

            conn.commit()
            conn.close()

            # Обновляем таблицу в диалоге
            self.load_access_logs()

            # Обновляем главное окно
            self.main_app.load_access_logs()

        except sqlite3.Error as e:
            messagebox.showerror(
                "Ошибка добавления",
                f"Не удалось добавить запись:\n{str(e)}",
                parent=self
            )

#основное окно
class MainWindow(tk.Tk):
    def __init__(self, db_file):
        super().__init__()
        self.db_file = db_file
        self.manager_id = None
        self.manager_name = None
        self.iconbitmap('logo.ico')
        self.configure(bg='#FFFFFF')
        self.title("Учет партнеров - Образ плюс")
        self.geometry("1000x600")

        try:
            import_warnings = initialize_db(self.db_file)
            if import_warnings:
                messagebox.showwarning("Warning", "\n".join(import_warnings))
            self.login()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать базу данных: {str(e)}")
            self.destroy()

    def init_ui(self):
        # Методы инициализации вкладок (теперь они могут безопасно обращаться к self.notebook)
        self.init_partners_tab()
        self.init_orders_tab()
        self.init_materials_tab()  # Переименовывать не нужно, если соблюдена последовательность
        self.init_employees_tab()
        self.init_access_tab()

        ttk.Label(self, text=f"Менеджер: {self.manager_name}").pack(anchor="ne", padx=10)

    def init_materials_tab(self):
        frame = ttk.Frame(self.materials_frame, padding="10")
        frame.pack(fill="both", expand=True)

        # Treeview для материалов
        self.materials_tree = ttk.Treeview(frame, columns=("ID", "Тип", "Название", "Поставщик", "Количество"),
                                           show="headings")
        self.materials_tree.pack(fill="both", expand=True)

        # Настройка колонок
        for col in ["ID", "Тип", "Название", "Поставщик", "Количество"]:
            self.materials_tree.heading(col, text=col)
            self.materials_tree.column(col, width=100)

        # Кнопки
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=5)

        ttk.Button(btn_frame, text="Обновить", command=self.load_materials).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Показать продукцию", command=self.show_products).pack(side="left", padx=5)

        # Загрузка данных
        self.load_materials()

    def on_material_select(self, event):
        """Активирует кнопку просмотра продукции при выборе материала"""
        selected = self.materials_table.focus()
        if selected:
            self.btn_show_products.config(state=tk.NORMAL)
        else:
            self.btn_show_products.config(state=tk.DISABLED)

    def show_products_for_material(self):
        """Открывает окно с продукцией для выбранного материала"""
        selected = self.materials_table.focus()
        if not selected:
            return

        material_id = self.materials_table.item(selected)["values"][0]
        ProductsForMaterialDialog(self, self.db_file, material_id)



    def login(self):
        LoginDialog(self, self.db_file, self.on_login)

    def on_login(self, manager_id, manager_name):
        self.manager_id = manager_id
        self.manager_name = manager_name
        self.init_ui()

    def init_ui(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.partners_frame = ttk.Frame(self.notebook)
        self.orders_frame = ttk.Frame(self.notebook)
        self.materials_frame = ttk.Frame(self.notebook)
        self.employees_frame = ttk.Frame(self.notebook)
        self.access_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.partners_frame, text="Партнеры")
        self.notebook.add(self.orders_frame, text="Заявки")
        self.notebook.add(self.materials_frame, text="Материалы")
        self.notebook.add(self.employees_frame, text="Кадры")
        self.notebook.add(self.access_frame, text="Доступ")

        ttk.Label(self, text=f"Менеджер: {self.manager_name}").pack(anchor="ne", padx=10)

        self.init_partners_tab()
        self.init_orders_tab()
        self.init_materials_tab()
        self.init_employees_tab()
        self.init_access_tab()

    def init_partners_tab(self):
        frame = ttk.Frame(self.partners_frame, padding="10")
        frame.grid(row=0, column=0, sticky="nsew")

        self.partners_table = ttk.Treeview(frame, columns=("ID", "Наименование", "Тип", "Рейтинг", "Адрес", "Директор", "Телефон", "Email", "ИНН"), show="headings")
        headers = ["ID", "Наименование", "Тип", "Рейтинг", "Адрес", "Директор", "Телефон", "Email", "ИНН"]
        for header in headers:
            self.partners_table.heading(header, text=header)
            self.partners_table.column(header, width=100)
            self.partners_table.grid(row=0, column=0, sticky="nsew")
            self.partners_table.bind("<Double-1>", self.edit_partner)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.partners_table.yview)
        self.partners_table.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Добавить партнера", command=self.add_partner).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="История продаж", command=self.view_sales).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Тест расчета материала", command=self.test_material_calculation).grid(row=0, column=2, padx=5)

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.partners_frame.columnconfigure(0, weight=1)
        self.partners_frame.rowconfigure(0, weight=1)

        self.load_partners()

    def init_orders_tab(self):
        frame = ttk.Frame(self.orders_frame, padding="10")
        frame.grid(row=0, column=0, sticky="nsew")

        self.orders_table = ttk.Treeview(frame, columns=("ID", "Партнер", "Продукт", "Количество", "Сумма", "Статус", "Дата создания"), show="headings")
        headers = ["ID", "Партнер", "Продукт", "Количество", "Сумма", "Статус", "Дата создания"]
        for header in headers:
            self.orders_table.heading(header, text=header)
            self.orders_table.column(header, width=100)
        self.orders_table.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.orders_table.yview)
        self.orders_table.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Создать заявку", command=self.create_order).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Обновить статус", command=self.update_order_status).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Отменить заявку", command=self.cancel_order).grid(row=0, column=2, padx=5)

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.orders_frame.columnconfigure(0, weight=1)
        self.orders_frame.rowconfigure(0, weight=1)

        self.load_orders()

    def init_employees_tab(self):
        frame = ttk.Frame(self.employees_frame, padding="10")
        frame.grid(row=0, column=0, sticky="nsew")

        # Создание таблицы сотрудников
        self.employees_table = ttk.Treeview(
            frame,
            columns=("ID", "ФИО", "Дата рождения", "Паспорт", "Банк", "Семья", "Здоровье"),
            show="headings",
            selectmode="browse"
        )

        headers = ["ID", "ФИО", "Дата рождения", "Паспорт", "Банк", "Семья", "Здоровье"]
        for header in headers:
            self.employees_table.heading(header, text=header)
            self.employees_table.column(header, width=100, anchor="w")

        self.employees_table.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.employees_table.yview)
        self.employees_table.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Фрейм для кнопок управления
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)

        ttk.Button(
            button_frame,
            text="Добавить сотрудника",
            command=self.add_employee
        ).grid(row=0, column=0, padx=5)

        # Кнопка для удаления сотрудника
        ttk.Button(
            button_frame,
            text="Удалить сотрудника",
            command=self.delete_employee,
            style="Danger.TButton"
        ).grid(row=0, column=1, padx=5)

        # Настройка адаптивности
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.employees_frame.columnconfigure(0, weight=1)
        self.employees_frame.rowconfigure(0, weight=1)

        # Загрузка данных
        self.load_employees()

    def delete_employee(self):
        """Удаляет выбранного сотрудника с подтверждением"""
        selected = self.employees_table.selection()

        if not selected:
            messagebox.showwarning("Ошибка", "Выберите сотрудника для удаления")
            return

        # Получаем ID выбранного сотрудника
        item = self.employees_table.item(selected[0])
        emp_id = item['values'][0]
        emp_name = item['values'][1]

        # Запрос подтверждения
        confirm = messagebox.askyesno(
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить сотрудника?\n{emp_name} (ID: {emp_id})",
            icon="warning"
        )

        if not confirm:
            return

        try:
            # Подключение к вашей БД
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Включаем проверку внешних ключей
            cursor.execute("PRAGMA foreign_keys = ON")

            # Пытаемся удалить сотрудника
            cursor.execute("DELETE FROM employees WHERE employee_id = ?", (emp_id,))

            if cursor.rowcount == 0:
                messagebox.showerror("Ошибка", "Сотрудник не найден в базе данных")
            else:
                conn.commit()
                messagebox.showinfo("Успех", "Сотрудник успешно удален")

            # Обновляем таблицу независимо от результата
            self.load_employees()

        except sqlite3.IntegrityError as e:
            # Обработка ошибки связанных данных
            messagebox.showerror(
                "Ошибка удаления",
                "Невозможно удалить сотрудника:\n"
                "Существуют связанные записи в других таблицах\n\n"
                f"Детали: {str(e)}"
            )
        except sqlite3.OperationalError as e:
            # Обработка других ошибок БД
            messagebox.showerror("Ошибка БД", f"Ошибка при работе с базой данных: {str(e)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла непредвиденная ошибка: {str(e)}")
        finally:
            try:
                if conn:
                    conn.close()
            except:
                pass

    def load_employees(self):
        """Загружает сотрудников из базы данных в таблицу"""
        # Очистка существующих данных
        for row in self.employees_table.get_children():
            self.employees_table.delete(row)

        conn = None
        try:
            # Подключение к вашей БД
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Получаем данные сотрудников
            cursor.execute("""
                           SELECT employee_id,
                                  name,
                                  birth_date,
                                  passport,
                                  bank_details,
                                  family_status,
                                  health_status
                           FROM employees
                           ORDER BY employee_id
                           """)

            # Вставляем данные в таблицу
            for row in cursor.fetchall():
                # Заменяем None на пустую строку для отображения
                formatted_row = [str(value) if value is not None else "" for value in row]
                self.employees_table.insert("", "end", values=formatted_row)

        except sqlite3.OperationalError as e:
            # Обработка ошибки отсутствия таблицы
            if "no such table" in str(e):
                messagebox.showerror(
                    "Ошибка таблицы",
                    "Таблица сотрудников не найдена в базе данных.\n"
                    "Убедитесь, что таблица 'employees' существует."
                )
            else:
                messagebox.showerror("Ошибка загрузки", f"Ошибка при загрузке сотрудников: {str(e)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка: {str(e)}")
        finally:
            try:
                if conn:
                    conn.close()
            except:
                pass

    def init_access_tab(self):
        frame = ttk.Frame(self.access_frame, padding="10")
        frame.grid(row=0, column=0, sticky="nsew")

        self.access_table = ttk.Treeview(frame, columns=("ID", "Сотрудник", "Дверь", "Время"), show="headings")
        headers = ["ID", "Сотрудник", "Дверь", "Время"]
        for header in headers:
            self.access_table.heading(header, text=header)
            self.access_table.column(header, width=100)
        self.access_table.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.access_table.yview)
        self.access_table.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Просмотреть журнал", command=self.view_access_log).grid(row=0, column=0, padx=5)

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.access_frame.columnconfigure(0, weight=1)
        self.access_frame.rowconfigure(0, weight=1)

        self.load_access_logs()

    def view_access_log(self):
        """Открывает диалоговое окно журнала доступа"""
        # Исправленный вызов с передачей всех необходимых параметров
        AccessLogDialog(self, self.db_file, self)  # Добавлен третий аргумент - ссылка на главное приложение

    def load_access_logs(self):
        """Загружает данные журнала доступа в главное окно"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Выбираем данные
            cursor.execute('''
                           SELECT a.log_id,
                                  e.name,
                                  a.door_id,
                                  a.timestamp
                           FROM access_logs a
                                    JOIN employees e ON a.employee_id = e.employee_id
                           ORDER BY a.timestamp DESC
                           ''')

            logs = cursor.fetchall()
            conn.close()

            # Очищаем таблицу
            for item in self.access_table.get_children():
                self.access_table.delete(item)

            # Заполняем данными
            for log in logs:
                self.access_table.insert("", "end", values=log)

        except sqlite3.Error as e:
            messagebox.showerror(
                "Ошибка базы данных",
                f"Не удалось загрузить журнал доступа:\n{str(e)}",
                parent=self
            )

    def load_partners(self):
        try:
            if not table_exists(self.db_file, 'partners'):
                messagebox.showerror("Ошибка", "Таблица 'partners' не существует.", parent=self)
                return
            for item in self.partners_table.get_children():
                self.partners_table.delete(item)

            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute('SELECT partner_id, name, partner_type, rating, address, director_name, phone, email, inn FROM partners')
            partners = cursor.fetchall()
            conn.close()

            print(f"Loaded {len(partners)} partners")
            for partner in partners:
                self.partners_table.insert("", "end", values=partner)
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить список партнеров: {str(e)}", parent=self)

    def load_orders(self):
        try:
            if not table_exists(self.db_file, 'orders'):
                messagebox.showerror("Ошибка", "Таблица 'orders' не существует.", parent=self)
                return
            for item in self.orders_table.get_children():
                self.orders_table.delete(item)

            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT o.order_id, p.name, pr.name, o.quantity, o.cost, o.status, o.created_date
                FROM orders o
                JOIN partners p ON o.partner_id = p.partner_id
                JOIN products pr ON o.product_id = pr.product_id
            ''')
            orders = cursor.fetchall()
            conn.close()

            print(f"Loaded {len(orders)} orders")
            for order in orders:
                self.orders_table.insert("", "end", values=order)

            self.check_preservation_timeouts()
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить заявки: {str(e)}", parent=self)

    def load_materials(self):
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute('''
                           SELECT m.material_id, m.type, m.name, s.name, m.stock_quantity
                           FROM materials m
                                    LEFT JOIN suppliers s ON m.supplier_id = s.supplier_id
                           ''')

            # Очистка таблицы
            for item in self.materials_tree.get_children():
                self.materials_tree.delete(item)

            # Заполнение данными
            for row in cursor.fetchall():
                self.materials_tree.insert("", "end", values=row)

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Ошибка загрузки материалов: {str(e)}")
        finally:
            if conn:
                conn.close()

    def show_products(self):
        selected = self.materials_tree.focus()
        if not selected:
            messagebox.showwarning("Ошибка", "Выберите материал")
            return

        material_id = self.materials_tree.item(selected)["values"][0]
        ProductsForMaterialDialog(self, self.db_file, material_id)

    def load_employees(self):
        try:
            if not table_exists(self.db_file, 'employees'):
                messagebox.showerror("Ошибка", "Таблица 'employees' не существует.", parent=self)
                return
            for item in self.employees_table.get_children():
                self.employees_table.delete(item)

            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute('SELECT employee_id, name, birth_date, passport, bank_details, family_status, health_status FROM employees')
            employees = cursor.fetchall()
            conn.close()

            print(f"Loaded {len(employees)} employees")
            for employee in employees:
                self.employees_table.insert("", "end", values=employee)
        except sqlite3.Error as e:
            print(f"Error loading employees: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось загрузить список сотрудников: {str(e)}", parent=self)

    def load_access_logs(self):
        try:
            if not table_exists(self.db_file, 'access_logs'):
                messagebox.showerror("Ошибка", "Таблица 'access_logs' не существует.", parent=self)
                return
            for item in self.access_table.get_children():
                self.access_table.delete(item)

            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.log_id, e.name, a.door_id, a.timestamp
                FROM access_logs a
                JOIN employees e ON a.employee_id = e.employee_id
            ''')
            logs = cursor.fetchall()
            conn.close()

            print(f"Loaded {len(logs)} access logs")
            for log in logs:
                self.access_table.insert("", "end", values=log)
        except sqlite3.Error as e:
            print(f"Error loading access logs: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось загрузить журнал доступа: {str(e)}", parent=self)

    def check_preservation_timeouts(self):
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT order_id, created_date, partner_id
                FROM orders
                WHERE status = 'created' AND prepayment_date IS NULL
            ''')
            orders = cursor.fetchall()
            for order_id, created_date, partner_id in orders:
                created = datetime.strptime(created_date, "%Y-%m-%d")
                if datetime.now() - created > timedelta(days=3):
                    cursor.execute("UPDATE orders SET status = 'cancelled' WHERE order_id = ?", (order_id,))
                    cursor.execute("SELECT email FROM partners WHERE partner_id = ?", (partner_id,))
                    email = cursor.fetchone()[0]
                    if email:
                        print(f"Order {order_id} cancelled due to timeout. Notified partner: {email}")
                    else:
                        print(f"Order {order_id} cancelled due to timeout. No email for partner_id={partner_id}")
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error checking prepayment timeouts: {str(e)}")
        finally:
            conn.close()

    def add_partner(self):
        PartnerDialog(self, self.db_file, self.manager_id)

    def edit_partner(self, event):
        selected_item = self.partners_table.selection()
        if not selected_item:
            return
        partner_id = int(self.partners_table.item(selected_item)['values'][0])
        PartnerDialog(self, self.db_file, self.manager_id, partner_id)

    def create_order(self):
        OrderDialog(self, self.db_file, self.manager_id)

    def update_order_status(self):
        selected_item = self.orders_table.selection()
        if not selected_item:
            messagebox.showwarning("Ошибка", "Выберите заявку для обновления статуса.", parent=self)
            return
        order_id = int(self.orders_table.item(selected_item)['values'][0])
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT order_id, status, product_id, quantity, partner_id FROM orders WHERE order_id = ?", (order_id,))
            order = cursor.fetchone()
            if not order:
                messagebox.showerror("Ошибка", "Заявка не найдена.", parent=self)
                conn.close()
                return
            _, current_status, product_id, quantity, partner_id = order
            status_map = {
                'created': 'prepaid',
                'prepaid': 'in_production',
                'in_production': 'delivered',
                'delivered': 'completed'
            }
            if current_status not in status_map:
                messagebox.showerror("Ошибка", f"Невозможный переход для статуса: {current_status}", parent=self)
                conn.close()
                return
            new_status = status_map[current_status]
            if new_status == 'prepaid':
                cursor.execute('UPDATE orders SET status = ?, prepayment_date = ? WHERE order_id = ?',
                              (new_status, datetime.now().strftime('%Y-%m-%d'), order_id))
            elif new_status == 'in_production':
                cursor.execute('SELECT stock_quantity FROM materials WHERE material_id = ?', (1,))
                material = cursor.fetchone()
                if not material or material[0] < quantity:
                    messagebox.showerror("Ошибка", "Недостаточно материала на складе.", parent=self)
                    conn.close()
                    return
                cursor.execute('UPDATE materials SET stock_quantity = stock_quantity - ? WHERE material_id = ?', (quantity, 1))
                cursor.execute('''
                    INSERT INTO warehouse_movements (material_id, product_id, quantity, movement_type, date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (1, product_id, quantity, 'outgoing', datetime.now().strftime('%Y-%m-%d')))
                cursor.execute('UPDATE orders SET status = ? WHERE order_id = ?', (new_status, order_id))
            elif new_status == 'completed':
                cursor.execute('UPDATE orders SET status = ?, completion_date = ? WHERE order_id = ?',
                              (new_status, datetime.now().strftime('%Y-%m-%d'), order_id))
                cursor.execute('SELECT email FROM partners WHERE partner_id = ?', (partner_id,))
                email = cursor.fetchone()[0]
            else:
                cursor.execute('UPDATE orders SET status = ? WHERE order_id = ?', (new_status, order_id))
            conn.commit()
            self.load_orders()
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Ошибка обновления статуса: {str(e)}", parent=self)
        finally:
            conn.close()

    def cancel_order(self):
        selected_item = self.orders_table.selection()
        if not selected_item:
            messagebox.showwarning("Ошибка", "Выберите заявку для отмены.", parent=self)
            return
        order_id = int(self.orders_table.item(selected_item)['values'][0])
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT status, partner_id FROM orders WHERE order_id = ?", (order_id,))
            order = cursor.fetchone()
            if not order:
                messagebox.showerror("Ошибка", "Заявка не найдена.", parent=self)
                conn.close()
                return
            status, partner_id = order
            if status not in ['created', 'prepaid']:
                messagebox.showwarning("Ошибка", "Можно отменить только заявки в статусе 'created' или 'prepaid'.", parent=self)
                conn.close()
                return
            cursor.execute("UPDATE orders SET status = 'cancelled' WHERE order_id = ?", (order_id,))
            cursor.execute("SELECT email FROM partners WHERE partner_id = ?", (partner_id,))
            email = cursor.fetchone()[0]
            conn.commit()
            self.load_orders()
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Ошибка отмены заявки: {str(e)}", parent=self)
        finally:
            conn.close()

    def view_sales(self):
        selected_item = self.partners_table.selection()
        if not selected_item:
            messagebox.showwarning("Ошибка", "Выберите партнера для просмотра истории продаж.", parent=self)
            return
        partner_id = int(self.partners_table.item(selected_item)['values'][0])
        SalesDialog(self, self.db_file, partner_id)

    def add_employee(self):
        EmployeeDialog(self, self.db_file)

    def view_access_log(self):
        AccessLogDialog(self, self.db_file, self)

    def test_material_calculation(self):
        try:
            selected_item = self.partners_table.selection()
            if not selected_item:
                messagebox.showwarning("Ошибка", "Выберите партнера для теста расчета материала.", parent=self)
                return
            partner_id = int(self.partners_table.item(selected_item)['values'][0])
            if partner_id != 1:
                messagebox.showinfo("Информация", "Тест расчета материала доступен только для партнера с ID=1.", parent=self)
                return
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.quantity, p.product_type_id, p.param1, p.param2
                FROM sales s
                JOIN products p ON s.product_id = p.product_id
                WHERE s.partner_id = ?
            ''', (partner_id,))
            sale = cursor.fetchone()
            conn.close()
            if not sale:
                messagebox.showerror("Ошибка", "Нет данных о продажах для этого партнера.", parent=self)
                return
            quantity, product_type_id, param1, param2 = sale
            material_type_id = 1
            result = calculate_products(product_type_id, material_type_id, quantity, param1, param2)
            if result == -1:
                messagebox.showerror("Ошибка", "Ошибка расчета материала для данной продукции.", parent=self)
            else:
                messagebox.showinfo("Результат", f"Расчет материала для partner_id={partner_id}: {result}", parent=self)
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Ошибка расчета: {str(e)}", parent=self)

class ProductsForMaterialDialog(tk.Toplevel):
        """Окно для отображения продукции, использующей выбранный материал"""

        def __init__(self, parent, db_file, material_id):
            super().__init__(parent)
            self.parent = parent
            self.db_file = db_file
            self.material_id = material_id

            self.title(f"Продукция для материала #{material_id}")
            self.geometry("600x400")
            self.transient(parent)
            self.grab_set()

            # Основной фрейм
            main_frame = ttk.Frame(self, padding="10")
            main_frame.pack(fill=tk.BOTH, expand=True)

            # Заголовок
            ttk.Label(
                main_frame,
                text=f"Продукция, использующая материал #{material_id}",
                font=("Arial", 12)
            ).pack(pady=5)

            # Таблица продукции
            self.tree = ttk.Treeview(
                main_frame,
                columns=("Продукт", "Количество материала"),
                show="headings"
            )
            self.tree.heading("Продукт", text="Продукт")
            self.tree.heading("Количество материала", text="Количество материала")
            self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            # Кнопка закрытия
            ttk.Button(
                main_frame,
                text="Закрыть",
                command=self.destroy
            ).pack(pady=5)

            # Загрузка данных
            self.load_data()

        def load_data(self):
            """Загружает данные о продукции для материала"""
            try:
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()

                cursor.execute("""
                               SELECT p.name,
                                      SUM(wm.quantity) as total_material
                               FROM products p
                                        JOIN
                                    warehouse_movements wm ON p.product_id = wm.product_id
                               WHERE wm.material_id = ?
                               GROUP BY p.product_id
                               """, (self.material_id,))

                # Очистка таблицы
                for row in self.tree.get_children():
                    self.tree.delete(row)

                # Заполнение данными
                for row in cursor.fetchall():
                    self.tree.insert("", tk.END, values=row)

            except sqlite3.Error as e:
                messagebox.showerror("Ошибка", f"Ошибка загрузки данных: {str(e)}", parent=self)
            finally:
                conn.close()

if __name__ == "__main__":
    try:
        app = MainWindow(DB_FILE)
        app.mainloop()
    except KeyboardInterrupt:
        print("Программа корректно завершена")
