from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import time
import queue
import os
import re

# Cola thread-safe para almacenar resultados
results_queue = queue.Queue()

# Límite máximo de publicaciones a procesar
MAX_POSTS = 600

class InstagramScraper:
    def __init__(self):
        self.driver = None
        self.logged_in = False
    
    def setup_driver(self):
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    def login_to_instagram(self, username, password):
        """Función para iniciar sesión en Instagram"""
        if self.logged_in:
            return True
            
        try:
            print("Intentando iniciar sesión en Instagram...")
            self.driver.get("https://www.instagram.com/accounts/login/")
            
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            
            username_field = self.driver.find_element(By.NAME, "username")
            password_field = self.driver.find_element(By.NAME, "password")
            
            username_field.clear()
            username_field.send_keys(username)
            password_field.clear()
            password_field.send_keys(password)
            
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            time.sleep(10)
            
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//section//main"))
            )
            
            print("Inicio de sesión exitoso")
            self.logged_in = True
            return True
            
        except Exception as e:
            print(f"Error al iniciar sesión: {e}")
            return False

    def close_popups(self):
        """Cierra cualquier popup que pueda aparecer en Instagram."""
        popup_selectors = [
            "button[data-testid='cookie-policy-banner-close']",
            "div[role='dialog'] button[type='button']",
            "button[aria-label='Close']",
            "button._a9--._a9_1",
            "button._acan._acap._acas"
        ]
        
        for selector in popup_selectors:
            try:
                buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for button in buttons:
                    if button.is_displayed():
                        try:
                            button.click()
                            time.sleep(1)
                        except:
                            self.driver.execute_script("arguments[0].click();", button)
                            time.sleep(1)
            except:
                pass

    def hover_over_post(self, element):
        try:
            # Scroll hasta el elemento para asegurarnos que está en la vista
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.5)  # Dar tiempo al desplazamiento

            # Hacer hover sobre el elemento
            actions = ActionChains(self.driver)
            actions.move_to_element(element).pause(1).perform()
            time.sleep(1.5)  # Esperar a que se muestren los datos del hover
            
            likes = 0
            comments = 0
            
            # ENFOQUE MEJORADO: Buscar específicamente en el overlay de métricas
            try:
                # Intentar encontrar el contenedor de métricas que aparece en hover
                metric_container = self.driver.find_element(
                    By.XPATH, 
                    "//div[contains(@class, 'x1qjc9v5') or contains(@class, 'x78zum5') or contains(@class, 'x1q0g3np')]"
                )
                
                if metric_container.is_displayed():
                    # Buscar todos los números en el contenedor
                    numbers = []
                    spans = metric_container.find_elements(By.XPATH, ".//span[contains(text(), '')]")
                    
                    for span in spans:
                        text = span.text.strip()
                        if text and re.search(r'\d', text):
                            num = self.extract_number(text)
                            # Aceptar 0 y cualquier cifra válida
                            if num >= 0:
                                numbers.append(num)
                    
                    # Filtrar los números específicos que queremos ignorar
                    numbers = [n for n in numbers if n not in [2025, 944, 95, 22]]
                    
                    # Eliminar duplicados
                    numbers = list(dict.fromkeys(numbers))
                    
                    # Ordenar los números encontrados para tener en cuenta comentarios y luego likes
                    numbers = sorted(numbers, reverse=True)
                    
                    if len(numbers) >= 2:
                        comments = numbers[0]  # El mayor número ahora es comentarios
                        likes = numbers[1]     # El segundo mayor número ahora es likes
                    elif len(numbers) == 1:
                        comments = numbers[0]  # Si solo hay un número, asumimos que son comentarios
                        
                    print(f"Números encontrados en métricas (filtrados): {numbers}")
                    
            except Exception as e:
                print(f"Error buscando contenedor de métricas: {e}")
            
            # Si no encontramos ambos valores, intentar métodos alternativos
            if not (likes != None and comments != None):  # Permitir el valor 0
                # Método alternativo: buscar spans con números en todo el documento
                try:
                    spans = self.driver.find_elements(
                        By.XPATH, 
                        "//span[contains(@class, 'html-span') or contains(@class, 'x1lliihq')]"
                    )
                    
                    numbers = []
                    for span in spans:
                        if span.is_displayed():
                            text = span.text.strip()
                            if text and re.search(r'\d', text):
                                num = self.extract_number(text)
                                # Aceptar 0 y cualquier cifra válida
                                if num >= 0:
                                    numbers.append(num)
                    
                    # Filtrar los números específicos que queremos ignorar
                    numbers = [n for n in numbers if n not in [2025, 944, 95, 22]]
                    
                    # Eliminar duplicados preservando el orden
                    numbers = list(dict.fromkeys(numbers))
                    
                    # Ordenar los números encontrados
                    numbers = sorted(numbers, reverse=True)
                    
                    if len(numbers) >= 2 and not (likes != None and comments != None):
                        comments = numbers[0]  # El mayor número ahora es comentarios
                        likes = numbers[1]     # El segundo mayor número ahora es likes
                    elif len(numbers) == 1 and comments == None:
                        comments = numbers[0]  # Si solo hay un número, asumimos que son comentarios
                        
                    print(f"Números encontrados en spans (filtrados): {numbers}")
                    
                except Exception as e:
                    print(f"Error en método alternativo de spans: {e}")
            
            # Método de fallback: buscar pares de números juntos (como "335\n1567")
            if not (likes != None and comments != None):
                try:
                    elements = self.driver.find_elements(
                        By.XPATH, 
                        "//*[contains(text(), '\n') and contains(text(), '')]"
                    )
                    
                    for el in elements:
                        if el.is_displayed():
                            text = el.text.strip()
                            if '\n' in text:
                                parts = text.split('\n')
                                nums = []
                                for part in parts:
                                    num = self.extract_number(part)
                                    # Aceptar 0 y cualquier cifra válida
                                    if num >= 0 and num not in [2025, 944, 95, 22]:
                                        nums.append(num)
                                
                                # Eliminar duplicados
                                nums = list(dict.fromkeys(nums))
                                
                                if len(nums) >= 2:
                                    comments = max(nums)  # El mayor número ahora es comentarios
                                    likes = min(nums)     # El menor número ahora es likes
                                    print(f"Encontrado par de números (filtrados): {nums}")
                                    break
                                    
                except Exception as e:
                    print(f"Error en método de pares de números: {e}")
            
            print(f"Valores finales extraídos - Comentarios: {comments}, Likes: {likes}")
            return comments, likes  # Invertido el orden de retorno para coincidir con la nueva lógica
            
        except Exception as e:
            print(f"Error general en hover_over_post: {e}")
            return 0, 0

    def extract_number(self, text):
        try:
            # Eliminar caracteres no numéricos excepto punto y coma
            text = re.sub(r'[^\d,.k]', '', text.lower())
            
            # Casos especiales con formato de miles (k)
            if 'k' in text:
                # 1.5k = 1500, 1k = 1000
                number_part = text.replace('k', '')
                try:
                    if '.' in number_part:
                        return int(float(number_part.replace(',', '.')) * 1000)
                    else:
                        return int(float(number_part) * 1000)
                except:
                    pass
                    
            # Casos numéricos normales
            # Primero intentar con el formato de punto decimal
            matches = re.findall(r'\d+(?:\.\d+)?', text.replace(',', '.'))
            if matches:
                return int(float(matches[0]))
            
            # Si no funcionó, intentar con formato de coma decimal
            matches = re.findall(r'\d+(?:,\d+)?', text)
            if matches:
                return int(float(matches[0].replace(',', '.')))
                
            return 0
        except Exception as e:
            print(f"Error extrayendo número de '{text}': {e}")
            return 0

    def is_video(self, element=None):
        """Determina si un post es un video"""
        try:
            if element:
                # Buscar indicadores de video en el elemento
                video_indicators = [
                    'svg[aria-label="Video"]',  # Icono de video
                    'video',                   # Elemento de video HTML
                    'span[aria-label="Reel"]'  # Indicador de Reels
                ]
                
                for indicator in video_indicators:
                    try:
                        elements = element.find_elements(By.CSS_SELECTOR, indicator)
                        if elements:
                            return True
                    except:
                        continue
                
                # Verificar si el enlace es de un reel
                link = element.get_attribute('href')
                if link and "/reel/" in link:
                    return True
                    
                return False
            else:
                # Método alternativo si no se proporciona elemento
                video_elements = self.driver.find_elements(By.TAG_NAME, 'video')
                return len(video_elements) > 0
        except Exception as e:
            print(f"Error al verificar si es video: {e}")
            return False

    def scroll_to_load_posts(self, max_posts=MAX_POSTS):
        SCROLL_PAUSE_TIME = 3
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        posts_info = []
        seen_links = set()
        
        post_selectors = [
            "//div[contains(@class, 'x1lliihq x1n2onr6 xh8yej3 x4gyw5p x11i5rnm x1ntc13c x9i3mqj')]//a",
            "//div[contains(@class, '_aagv')]//a",
            "//article//a[contains(@href, '/p/') or contains(@href, '/reel/')]"
        ]
        
        while len(posts_info) < max_posts:
            self.close_popups()
            
            current_posts = []
            for selector in post_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for el in elements:
                        link = el.get_attribute('href')
                        if link and link not in seen_links and ("/p/" in link or "/reel/" in link):
                            seen_links.add(link)
                            current_posts.append({
                                'link': link,
                                'element': el
                            })
                except Exception as e:
                    print(f"Error con selector {selector}: {e}")
            
            for post in current_posts:
                if len(posts_info) >= max_posts:
                    break
                
                try:
                    # Hacer hover sobre el post para obtener likes y comentarios
                    likes, comments = self.hover_over_post(post['element'])
                    
                    # Determinar si es video
                    is_video_post = self.is_video(post['element'])
                    
                    posts_info.append({
                        'link': post['link'],
                        'is_video': is_video_post,
                        'type': "Video" if is_video_post else "Imagen",
                        'likes': likes,
                        'comments': comments
                    })
                except Exception as e:
                    print(f"Error procesando post: {e}")
            
            print(f"Posts encontrados: {len(posts_info)}/{max_posts}")
            
            if len(posts_info) >= max_posts:
                break
            
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SCROLL_PAUSE_TIME)
            
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                for _ in range(3):
                    self.driver.execute_script("window.scrollBy(0, 500);")
                    time.sleep(1)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    print("No hay más contenido para cargar")
                    break
            last_height = new_height
        
        return posts_info[:max_posts]

    def process_post(self, post_info, index, total_posts):
        try:
            post_link = post_info['link']
            print(f"Procesando post {index}/{total_posts}: {post_link}")
            
            # Usar los valores capturados durante el hover previo
            post_data = {
                "Número de Post": index,
                "URL del Post": post_link,
                "Es Video": "Sí" if post_info.get('is_video', False) else "No",
                "Tipo": post_info.get('type', 'Desconocido'),
                "Likes": post_info.get('likes', 0),
                "Comentarios": post_info.get('comments', 0),
                "Fecha": "N/A",
                "Reproducciones": "N/A"
            }
            
            results_queue.put(post_data)
            return True
            
        except Exception as e:
            print(f"Error al procesar el post {index}: {e}")
            minimal_data = {
                "Número de Post": index,
                "URL del Post": post_info['link'],
                "Es Video": "Error",
                "Tipo": "Error",
                "Descripción": "Error",
                "Likes": 0,
                "Comentarios": 0,
                "Fecha": "N/A",
                "Reproducciones": "N/A"
            }
            results_queue.put(minimal_data)
            return False

    def scrape_profile(self, target_profile, username=None, password=None, max_posts=MAX_POSTS, csv_filename="instagram_data"):
        try:
            self.setup_driver()
            
            if username and password:
                if not self.login_to_instagram(username, password):
                    print("No se pudo iniciar sesión. Continuando sin login...")
            
            self.driver.get(f"https://www.instagram.com/{target_profile}/")
            self.close_popups()
            time.sleep(3)
            
            print(f"Cargando posts (máximo {max_posts})...")
            posts_info = self.scroll_to_load_posts(max_posts)
            
            total_posts = len(posts_info)
            print(f"Total de posts a procesar: {total_posts}")
            
            results = []
            for i, post in enumerate(posts_info, 1):
                self.process_post(post, i, total_posts)
                while not results_queue.empty():
                    results.append(results_queue.get())
                
                if i % 10 == 0:
                    self.save_to_csv(results, f"{csv_filename}_parcial")
                    print(f"Guardado parcial realizado ({i} posts procesados)")
            
            self.save_to_csv(results, csv_filename)
            print(f"Datos guardados en {csv_filename}.csv")
            return True
            
        except Exception as e:
            print(f"Error general: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()

    def save_to_csv(self, posts_data, filename):
        if not posts_data:
            print("No hay datos para guardar.")
            return
        
        fieldnames = ["Número de Post", "Es Video", "Tipo", "Likes", 
                      "Comentarios", "Fecha", "URL del Post", "Reproducciones"]
        
        with open(f'{filename}.csv', 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(posts_data)

if __name__ == "__main__":
    print("=========== INSTAGRAM SCRAPER ===========")
    
    scraper = InstagramScraper()
    
    use_login = input('¿Deseas iniciar sesión automáticamente? (s/n): ').lower() == 's'
    username = None
    password = None
    
    if use_login:
        username = 'vento.norteoficial'
        password = 'Latin2025!'
    
    target_profile = 'postamx'
    filename = input('Nombre del archivo .csv: ')
    max_posts = int(input('Número máximo de posts (máximo 600): '))
    
    if max_posts > 600:
        max_posts = 600
        print("Se ha limitado a 600 posts")
    
    scraper.scrape_profile(
        target_profile=target_profile,
        username=username,
        password=password,
        max_posts=max_posts,
        csv_filename=filename
    )