import os
import csv
import time
import random
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

def set_chrome_options():
    """Configura las opciones de Chrome para la automatización."""
    chrome_options = Options()
    #chrome_options.add_argument("--headless")  # Comentar para ver el navegador
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-infobars")
    
    # Desactivar mensajes de error de WebGL
    chrome_options.add_argument("--disable-gl-error-logging")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--enable-unsafe-swiftshader")
    
    # Mejor simulación de un usuario real
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36")
    
    # Configuración para evitar el selector de perfiles en Windows
    profile_dir = os.path.join(os.getcwd(), "chrome_profile")
    if not os.path.exists(profile_dir):
        os.makedirs(profile_dir)
    
    # Especificar perfil 'Default' para evitar el selector de perfiles
    default_profile = os.path.join(profile_dir, "Default")
    if not os.path.exists(default_profile):
        os.makedirs(default_profile)
    
    chrome_options.add_argument(f"--user-data-dir={profile_dir}")
    chrome_options.add_argument("--profile-directory=Default")
    
    # Reducir la huella digital
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # Configuración avanzada para evitar detección
    prefs = {
        "profile.default_content_setting_values.notifications": 2,  # Bloquear notificaciones
        "profile.managed_default_content_settings.images": 1,  # Cargar imágenes
        "profile.managed_default_content_settings.javascript": 1,  # Permitir JavaScript
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    return chrome_options

def convert_count_to_number(count_str):
    """Convierte strings de conteo como '13.3K' o '1.2M' a números enteros"""
    try:
        if not count_str:
            return 0
            
        clean_str = count_str.strip()
        if 'K' in clean_str:
            return int(float(clean_str.replace('K', '')) * 1000)
        elif 'M' in clean_str:
            return int(float(clean_str.replace('M', '')) * 1000000)
        elif 'B' in clean_str:
            return int(float(clean_str.replace('B', '')) * 1000000000)
        else:
            return int(clean_str.replace(',', ''))
    except (ValueError, AttributeError):
        return 0

def wait_for_element(driver, css_selector, timeout=10):
    """Espera a que un elemento esté presente en la página con un manejo de errores mejorado."""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
        )
        return element
    except TimeoutException:
        return None

def check_for_captcha(driver):
    """Verifica si hay un CAPTCHA presente y espera a que se resuelva."""
    # Detectar posibles indicadores de CAPTCHA
    captcha_indicators = [
        "//div[contains(text(), 'CAPTCHA')]",
        "//div[contains(text(), 'captcha')]",
        "//div[contains(text(), 'Verify')]",
        "//div[contains(text(), 'verificar')]",
        "//iframe[contains(@src, 'captcha')]",
        "//h2[contains(text(), 'Verificación de seguridad')]",
        "//p[contains(text(), 'Something went wrong')]",
        "//p[contains(text(), 'verification')]",
        "//h1[contains(text(), 'Security Verification')]"
    ]
    
    for indicator in captcha_indicators:
        try:
            if driver.find_elements(By.XPATH, indicator):
                print("⚠️ CAPTCHA detectado! Por favor, resuélvelo manualmente.")
                print("⚠️ La interfaz puede cambiar dependiendo de la verificación.")
                print("⚠️ Completa la verificación de seguridad y luego continúa.")
                input("✅ Presiona Enter cuando hayas resuelto el CAPTCHA...")
                time.sleep(2)  # Dar tiempo para que la página se actualice después del CAPTCHA
                return True
        except:
            pass
    
    return False

def human_like_scroll(driver, scroll_amount=None):
    """Realiza un scroll que imita el comportamiento humano."""
    if scroll_amount is None:
        # Scroll aleatorio entre 100 y 800 píxeles
        scroll_amount = random.randint(300, 800)
    
    # Ejecutar el scroll con una velocidad variable
    driver.execute_script(f"""
    (function() {{
        const start = window.scrollY;
        const change = {scroll_amount};
        const duration = {random.randint(500, 1500)};
        let startTime = null;
        
        function animation(currentTime) {{
            if (startTime === null) startTime = currentTime;
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Función de ease-out para que el scroll parezca más natural
            const easeProgress = 1 - Math.pow(1 - progress, 3);
            
            window.scrollTo(0, start + change * easeProgress);
            
            if (progress < 1) {{
                window.requestAnimationFrame(animation);
            }}
        }}
        
        window.requestAnimationFrame(animation);
    }})();
    """)
    
    # Esperar a que termine la animación
    time.sleep(random.uniform(0.5, 1.5))

def close_popups(driver):
    """Cierra cualquier popup que pueda aparecer."""
    popup_selectors = [
        "button[data-e2e='cookie-banner-close']",
        "button[data-e2e='modal-close-inner-button']",
        "button.tiktok-btn-pc-primary",
        "button.decline-button",
        "button.button-primary",
        "button.close-button",
        "button[aria-label='Close']",
        "div.modal-close",
        "[data-testid='close-button']"
    ]
    
    for selector in popup_selectors:
        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, selector)
            for button in buttons:
                if button.is_displayed():
                    button.click()
                    print(f"Popup cerrado con selector: {selector}")
                    time.sleep(1)
        except Exception as e:
            pass

def scroll_page(driver, max_scrolls=10):
    """Desplaza la página hacia abajo para cargar más videos."""
    # Intentar diferentes selectores para videos/posts
    post_selectors = [
        "div[data-e2e='user-post-item']",
        "div.video-feed-item",
        "div.tiktok-x6y88p-DivItemContainerV2",
        "div.css-1as5cen-DivItemContainer",
        "div[data-e2e='user-post-item-container']"
    ]
    
    # Encontrar el selector que funciona
    video_selector = None
    for selector in post_selectors:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        if elements:
            video_selector = selector
            print(f"Usando selector: {selector} - Encontrados: {len(elements)} elementos")
            break
    
    if not video_selector:
        print("⚠️ No se puede identificar el selector de videos. Probando con el valor por defecto.")
        video_selector = "div[data-e2e='user-post-item']"
    
    video_count = len(driver.find_elements(By.CSS_SELECTOR, video_selector))
    
    scroll_count = 0
    no_new_videos_count = 0
    
    while scroll_count < max_scrolls:
        # Verificar si hay un CAPTCHA antes de hacer scroll
        if check_for_captcha(driver):
            print("CAPTCHA resuelto, continuando...")
        
        # Cerrar cualquier popup que aparezca
        close_popups(driver)
        
        # Hacer scroll de manera más humana
        human_like_scroll(driver)
        
        # Esperar un tiempo aleatorio entre scrolls (más realista)
        time.sleep(random.uniform(2, 5))
        
        # Verificar si se cargaron nuevos videos
        new_videos = len(driver.find_elements(By.CSS_SELECTOR, video_selector))
        
        print(f"Videos cargados: {new_videos}")
        
        # Si no se cargan más videos después de varios intentos, detenerse
        if new_videos == video_count:
            no_new_videos_count += 1
            if no_new_videos_count >= 3:  # Intentar 3 veces antes de rendirse
                print("No se detectaron más videos después de varios intentos. Finalizando carga.")
                break
        else:
            no_new_videos_count = 0
        
        # Actualizar conteo de videos
        video_count = new_videos
        scroll_count += 1
        
        # Pausa aleatoria ocasionalmente para parecer más humano
        if random.random() < 0.3:  # 30% de probabilidad
            pause_time = random.uniform(3, 8)
            print(f"Haciendo una pausa de {pause_time:.1f} segundos...")
            time.sleep(pause_time)
    
    return video_count, video_selector

def extract_videos_from_profile(username, max_videos):
    """Extrae las URLs de los videos de un perfil de TikTok."""
    chrome_options = set_chrome_options()
    driver = webdriver.Chrome(options=chrome_options)
    video_urls = []
    videos_data = []
    
    try:
        print("Inicializando navegador principal...")
        
        # Visitar primero la página principal para establecer cookies
        driver.get("https://www.tiktok.com/")
        time.sleep(random.uniform(3, 5))
        
        # Cerrar popups iniciales
        close_popups(driver)
        
        profile_url = f"https://www.tiktok.com/@{username}"
        print(f"Navegando a: {profile_url}")
        driver.get(profile_url)
        
        # Verificar CAPTCHA inicial
        check_for_captcha(driver)
        
        # Esperar a que se cargue el perfil y manejar la situación si no aparecen elementos
        print("Esperando carga de la página de perfil...")
        time.sleep(5)  # Añadir un tiempo de espera inicial
        
        # Intentar diferentes selectores para la carga de página
        loaded = False
        load_indicators = [
            "div[data-e2e='user-post-item']",
            "div.video-feed-item",
            "div.tiktok-x6y88p-DivItemContainerV2",
            "div[data-e2e='user-post-item-container']",
            "div[data-e2e='user-profile-header']"
        ]
        
        for indicator in load_indicators:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, indicator))
                )
                loaded = True
                print(f"Página cargada correctamente (indicador: {indicator})")
                break
            except TimeoutException:
                continue
        
        if not loaded:
            print("⚠️ No se detectaron indicadores de carga. Verificar visualmente.")
            print("⚠️ Si la página no cargó, puede haber un CAPTCHA o cambios en la estructura de la página.")
            check_for_captcha(driver)
            input("✅ Presiona Enter cuando la página haya cargado completamente o hayas resuelto cualquier CAPTCHA...")
        
        print("Comenzando a cargar videos mediante scroll...")
        video_count, video_selector = scroll_page(driver)
        
        # Obtener todas las URLs de videos y sus vistas
        video_elements = driver.find_elements(By.CSS_SELECTOR, video_selector)
        
        # Si se encontraron videos, procesarlos
        if video_elements:
            for i, video_element in enumerate(video_elements):
                if i >= max_videos:
                    break
                    
                try:
                    # Intentar extraer URL del video de diferentes maneras
                    video_url = None
                    
                    # Método 1: Buscar un enlace directo dentro del elemento
                    try:
                        video_link_element = video_element.find_element(By.TAG_NAME, "a")
                        video_url = video_link_element.get_attribute("href")
                    except (NoSuchElementException, StaleElementReferenceException):
                        pass
                    
                    # Método 2: Buscar cualquier enlace en un subelemento
                    if not video_url:
                        try:
                            links = video_element.find_elements(By.CSS_SELECTOR, "a[href*='tiktok.com']")
                            if links:
                                video_url = links[0].get_attribute("href")
                        except (NoSuchElementException, StaleElementReferenceException):
                            pass
                    
                    # Método 3: Usar el enlace del div padre si es que existe
                    if not video_url:
                        try:
                            # Subir a los padres para encontrar un enlace
                            parent = driver.execute_script("return arguments[0].parentNode;", video_element)
                            for _ in range(3):  # Intentar con varios niveles de padres
                                try:
                                    parent_links = parent.find_elements(By.TAG_NAME, "a")
                                    if parent_links:
                                        video_url = parent_links[0].get_attribute("href")
                                        if video_url and "tiktok.com" in video_url:
                                            break
                                    parent = driver.execute_script("return arguments[0].parentNode;", parent)
                                except:
                                    break
                        except:
                            pass
                    
                    # Método 4: Hacer clic en el elemento y obtener la URL de la nueva página
                    if not video_url:
                        try:
                            # Guardar la URL actual
                            current_url = driver.current_url
                            # Hacer clic en el elemento del video
                            video_element.click()
                            # Esperar a que cambie la URL
                            WebDriverWait(driver, 5).until(lambda d: d.current_url != current_url)
                            # Obtener la nueva URL
                            video_url = driver.current_url
                            # Volver a la página del perfil
                            driver.get(profile_url)
                            # Esperar a que la página cargue nuevamente
                            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, video_selector)))
                            # Obtener la lista actualizada de videos
                            video_elements = driver.find_elements(By.CSS_SELECTOR, video_selector)
                        except:
                            # Si algo falla, volver a la página de perfil
                            driver.get(profile_url)
                            time.sleep(3)
                            video_elements = driver.find_elements(By.CSS_SELECTOR, video_selector)
                    
                    # Si no se pudo obtener la URL, generar un mensaje de error y continuar
                    if not video_url:
                        print(f"❌ No se pudo extraer la URL del video {i+1}")
                        continue
                    
                    # Extraer vistas del video
                    views_count = 0
                    try:
                        views_selectors = [
                            "strong[data-e2e='video-views']", 
                            "span[data-e2e='video-views']",
                            "strong.video-count", 
                            "span.video-count"
                        ]
                        
                        for selector in views_selectors:
                            try:
                                views_elements = video_element.find_elements(By.CSS_SELECTOR, selector)
                                if views_elements:
                                    views_text = views_elements[0].text
                                    views_count = convert_count_to_number(views_text)
                                    if views_count > 0:
                                        break
                            except:
                                continue
                    except Exception as e:
                        print(f"Error al extraer las vistas: {str(e)}")
                    
                    # Añadir a las listas
                    print(f"Video {i+1}: {video_url} - Vistas: {views_count}")
                    video_urls.append(video_url)
                    videos_data.append({
                        'url': video_url,
                        'views': views_count
                    })
                except Exception as e:
                    print(f"Error al extraer datos del video {i+1}: {str(e)}")
        else:
            print("❌ No se encontraron videos en el perfil o el selector no es válido.")
            
    except Exception as e:
        print(f"Error al extraer videos del perfil: {str(e)}")
    finally:
        try:
            # No cerramos el driver principal, lo pasamos al procesamiento para reusarlo
            return driver, video_urls, videos_data
        except:
            if driver:
                driver.quit()
            return None, video_urls, videos_data

def process_video(driver, video_url, video_data, index, total):
    """Procesa un video individual y extrae sus datos. Reutiliza el driver existente."""
    try:
        print(f"[{index}/{total}] Procesando: {video_url}")
        driver.get(video_url)
        
        # Verificar CAPTCHA antes de continuar
        check_for_captcha(driver)
        
        # Cerrar cualquier popup que aparezca
        close_popups(driver)
        
        # Esperar a que cargue el video con diferentes posibles elementos
        video_loaded = False
        video_selectors = [
            ".tiktok-1itcwxg-ImgPoster", 
            "video", 
            "div[data-e2e='browse-video']", 
            "div[data-e2e='video-container']",
            "canvas[data-e2e='browse-video']",
            "div.css-1us9sro-DivAside"
        ]
        
        for selector in video_selectors:
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                video_loaded = True
                print(f"Video cargado con selector: {selector}")
                break
            except TimeoutException:
                continue
        
        if not video_loaded:
            print(f"⚠️ No se detectaron elementos de video. Esperando carga manual...")
            check_for_captcha(driver)
            input("✅ Presiona Enter cuando el video haya cargado o hayas resuelto cualquier CAPTCHA...")
        
        # Simulación de comportamiento humano
        time.sleep(random.uniform(1, 3))
        human_like_scroll(driver, random.randint(100, 300))  # Scroll suave hacia abajo
        
        # Extraer datos adicionales del video
        try:
            # Descripción del video (probando diferentes selectores)
            description = ""
            description_selectors = [
                "div[data-e2e='browse-video-desc']", 
                "span[data-e2e='video-desc']", 
                ".video-meta-description",
                "h1.tiktok-1eqe95p-H1VideoTitle",
                "div.tiktok-1wrhn5c-DivContainer"
            ]
            
            for selector in description_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        description = elements[0].text
                        if description:
                            break
                except:
                    pass
        except:
            description = ""
        
        try:
            # Fecha de publicación (probando diferentes selectores)
            date = ""
            date_selectors = [
                "span[data-e2e='browser-nickname'] + span", 
                "span[data-e2e='video-create-time']", 
                ".video-meta-date",
                "span.tiktok-14hp4um-SpanSubInfoText"
            ]
            
            for selector in date_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        date = elements[0].text
                        if date:
                            break
                except:
                    pass
        except:
            date = ""
        
        try:
            # Número de likes
            likes_count = 0
            likes_selectors = [
                "strong[data-e2e='like-count']", 
                "span[data-e2e='like-count']",
                "strong.engagement-count-like",
                "span.video-meta-like"
            ]
            
            for selector in likes_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        likes = elements[0].text
                        likes_count = convert_count_to_number(likes)
                        if likes_count > 0:
                            break
                except:
                    pass
        except:
            likes_count = 0
        
        try:
            # Número de comentarios
            comments_count = 0
            comments_selectors = [
                "strong[data-e2e='comment-count']", 
                "span[data-e2e='comment-count']",
                "strong.engagement-count-comment",
                "span.video-meta-comment"
            ]
            
            for selector in comments_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        comments = elements[0].text
                        comments_count = convert_count_to_number(comments)
                        if comments_count > 0:
                            break
                except:
                    pass
        except:
            comments_count = 0
        
        try:
            # Si no tenemos las vistas del feed, obtenerlas del video individual
            if 'views' not in video_data or video_data['views'] == 0:
                views_selectors = [
                    "strong[data-e2e='video-views']", 
                    "span[data-e2e='video-views']", 
                    ".video-meta-views",
                    "strong.video-count"
                ]
                
                for selector in views_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            views_text = elements[0].text
                            view_count = convert_count_to_number(views_text)
                            if view_count > 0:
                                video_data['views'] = view_count
                                break
                    except:
                        pass
        except:
            if 'views' not in video_data:
                video_data['views'] = 0
        
        # Completar el diccionario con todos los datos
        video_data.update({
            'description': description,
            'date': date,
            'likes': likes_count,
            'comments': comments_count
        })
        
        # Imprimir los datos obtenidos
        print(f"✅ Datos extraídos para video {index}:")
        print(f"   Descripción: {description[:50]}..." if len(description) > 50 else f"   Descripción: {description}")
        print(f"   Fecha: {date}")
        print(f"   Likes: {likes_count}")
        print(f"   Comentarios: {comments_count}")
        print(f"   Vistas: {video_data['views']}")
        
        # Simular comportamiento humano entre videos
        time.sleep(random.uniform(2, 4))
        
        return video_data
        
    except Exception as e:
        print(f"❌ Error al procesar el video {index}: {str(e)}")
        # Intentar verificar si hay un CAPTCHA presente
        try:
            check_for_captcha(driver)
        except:
            pass
        return video_data  # Devolver los datos parciales en caso de error

def save_to_csv(data, filename):
    """Guarda los datos extraídos en un archivo CSV."""
    try:
        with open(f"{filename}.csv", 'w', newline='', encoding='utf-8') as f:
            if data:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
                print(f"✅ Datos guardados exitosamente en {filename}.csv")
            else:
                print("⚠️ No hay datos para guardar.")
    except Exception as e:
        print(f"❌ Error al guardar los datos: {str(e)}")

def main():
    print("=" * 60)
    print("   EXTRACTOR DE DATOS DE VIDEOS DE TIKTOK")
    print("=" * 60)
    
    username = input("📱 Introduce la cuenta de TikTok: ")
    csv_filename = input("📄 Nombre del archivo CSV (sin extensión): ")
    max_videos = int(input("🔢 Número máximo de videos a extraer (recomendado 50-100): "))
    
    print("\n🚀 Iniciando extracción de datos...")
    
    # Obtener URLs de videos y datos básicos, junto con el driver principal
    main_driver, video_urls, videos_data = extract_videos_from_profile(username, max_videos)
    
    print(f"🔍 Total de videos encontrados: {len(video_urls)}")
    
    # Procesar videos secuencialmente para evitar múltiples CAPTCHAs
    if video_urls:
        print(f"Procesando {len(video_urls)} videos secuencialmente...")
        
        results = []
        try:
            if main_driver:
                # Pausa para revisar cualquier CAPTCHA pendiente antes de continuar
                check_for_captcha(main_driver)
                
                # Configurar tiempo entre requests para evitar detección
                min_delay = 5  # Tiempo mínimo entre videos (segundos)
                max_delay = 12  # Tiempo máximo entre videos (segundos)
                
                # Contador para pausas más largas
                long_pause_counter = 0
                
                for i, (url, data) in enumerate(zip(video_urls, videos_data)):
                    try:
                        # Añadir una pausa aleatoria entre cada solicitud
                        if i > 0:
                            delay = random.uniform(min_delay, max_delay)
                            print(f"Esperando {delay:.1f} segundos antes del siguiente video...")
                            time.sleep(delay)
                        
                        # Procesar el video con el driver principal
                        result = process_video(main_driver, url, data, i+1, len(video_urls))
                        if result:
                            results.append(result)
                        
                        # Incrementar contador
                        long_pause_counter += 1
                        
                        # De vez en cuando hacer una pausa más larga para parecer humano
                        if long_pause_counter >= 5:
                            long_pause = random.uniform(15, 30)
                            print(f"Haciendo una pausa más larga de {long_pause:.1f} segundos...")
                            time.sleep(long_pause)
                            long_pause_counter = 0
                        
                        # Guardar resultados parciales cada 10 videos
                        if i > 0 and i % 10 == 0:
                            save_to_csv(results, f"{csv_filename}_parcial")
                            print(f"💾 Guardado parcial realizado ({i} videos procesados)")
                    
                    except Exception as e:
                        print(f"Error al procesar video {i+1}: {str(e)}")
                        # Intentar continuar con el siguiente video
                        continue
            else:
                print("❌ No se pudo inicializar el navegador principal correctamente.")
        except Exception as e:
            print(f"Error durante el procesamiento: {str(e)}")
        finally:
            if main_driver:
                main_driver.quit()
                print("Navegador principal cerrado correctamente")
        
        # Guardar resultados en CSV
        save_to_csv(results, csv_filename)
        print(f"🎉 Se procesaron exitosamente {len(results)} videos.")
    else:
        print("❌ No se encontraron videos en el perfil.")
        if main_driver:
            main_driver.quit()
            print("Navegador cerrado")

def show_menu():
    """Muestra un menú de opciones para el usuario."""
    print("\n" + "=" * 60)
    print("   MENÚ DE OPCIONES")
    print("=" * 60)
    print("1. Extraer datos de videos de un perfil de TikTok")
    print("2. Salir")
    print("-" * 60)
    option = input("Selecciona una opción (1-2): ")
    return option

if __name__ == "__main__":
    try:
        print("\n✨ Bienvenido al Extractor de Datos de TikTok ✨")
        print("Este script permite extraer datos de videos de perfiles de TikTok.")
        print("NOTA: Es posible que necesites resolver CAPTCHAs durante el proceso.\n")
        
        while True:
            option = show_menu()
            if option == "1":
                main()
                print("\nOperación completada. Puedes revisar el archivo CSV generado.")
            elif option == "2":
                print("\n🙋‍♂️ ¡Gracias por usar el Extractor de Datos de TikTok!")
                break
            else:
                print("\n❌ Opción inválida. Por favor, selecciona una opción válida.")
    except KeyboardInterrupt:
        print("\n\n⚠️ Proceso interrumpido por el usuario.")
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")
    finally:
        print("\n👋 Programa finalizado.")