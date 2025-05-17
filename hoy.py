import os
import csv
import time
import random
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def set_chrome_options():
    """Configura las opciones de Chrome para la automatización."""
    chrome_options = Options()
    #chrome_options.add_argument("--headless")  # Comentar para ver el navegador
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-infobars")
    
    # Mejor simulación de un usuario real
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36")
    
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

def check_for_captcha(driver):
    """Verifica si hay un CAPTCHA presente y espera a que se resuelva."""
    # Detectar posibles indicadores de CAPTCHA
    captcha_indicators = [
        "//div[contains(text(), 'CAPTCHA')]",
        "//div[contains(text(), 'captcha')]",
        "//div[contains(text(), 'Verify')]",
        "//div[contains(text(), 'verificar')]",
        "//iframe[contains(@src, 'captcha')]",
        "//h2[contains(text(), 'Verificación de seguridad')]"
    ]
    
    for indicator in captcha_indicators:
        try:
            if driver.find_elements(By.XPATH, indicator):
                print("⚠️ CAPTCHA detectado! Por favor, resuélvelo manualmente.")
                input("✅ Presiona Enter cuando hayas resuelto el CAPTCHA...")
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

def scroll_page(driver, max_scrolls=10):
    """Desplaza la página hacia abajo para cargar más videos."""
    video_count = len(driver.find_elements(By.CSS_SELECTOR, "div[data-e2e='user-post-item']"))
    
    scroll_count = 0
    no_new_videos_count = 0
    
    while scroll_count < max_scrolls:
        # Verificar si hay un CAPTCHA antes de hacer scroll
        if check_for_captcha(driver):
            print("CAPTCHA resuelto, continuando...")
        
        # Hacer scroll de manera más humana
        human_like_scroll(driver)
        
        # Esperar un tiempo aleatorio entre scrolls (más realista)
        time.sleep(random.uniform(2, 5))
        
        # Verificar si se cargaron nuevos videos
        new_videos = len(driver.find_elements(By.CSS_SELECTOR, "div[data-e2e='user-post-item']"))
        
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
    
    return video_count

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
        
        # Verificar si hay un popup de cookies o configuración inicial
        try:
            # Buscar y cerrar posibles popups (específico para Windows)
            popup_selectors = [
                "button[data-e2e='cookie-banner-close']",
                "button[data-e2e='modal-close-inner-button']",
                "button.tiktok-btn-pc-primary",
                "button.decline-button",
                "button.button-primary"
            ]
            
            for selector in popup_selectors:
                try:
                    buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                    if buttons:
                        for button in buttons:
                            if button.is_displayed():
                                button.click()
                                time.sleep(1)
                                print(f"Popup cerrado con selector: {selector}")
                except Exception as e:
                    pass
        except:
            pass
        
        profile_url = f"https://www.tiktok.com/@{username}"
        print(f"Navegando a: {profile_url}")
        driver.get(profile_url)
        
        # Verificar CAPTCHA inicial
        check_for_captcha(driver)
        
        try:
            # Esperar a que se cargue el perfil
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-e2e='user-post-item']"))
            )
        except TimeoutException:
            print("⚠️ Tiempo de espera agotado al cargar la página principal")
            print("⚠️ Si aparece un CAPTCHA, resuélvelo manualmente.")
            input("✅ Presiona Enter cuando la página haya cargado completamente y hayas resuelto cualquier CAPTCHA...")
        
        print("Comenzando a cargar videos mediante scroll...")
        video_count = scroll_page(driver)
        
        # Obtener todas las URLs de videos y sus vistas
        video_elements = driver.find_elements(By.CSS_SELECTOR, "div[data-e2e='user-post-item']")
        
        for i, video_element in enumerate(video_elements):
            if i >= max_videos:
                break
                
            try:
                # Extraer URL del video
                video_link_element = video_element.find_element(By.CSS_SELECTOR, "a")
                video_url = video_link_element.get_attribute("href")
                
                # Extraer vistas del video
                try:
                    views_element = video_element.find_element(By.CSS_SELECTOR, "strong[data-e2e='video-views']")
                    views_text = views_element.text
                    views_count = convert_count_to_number(views_text)
                except NoSuchElementException:
                    views_count = 0
                
                # Añadir a las listas
                video_urls.append(video_url)
                videos_data.append({
                    'url': video_url,
                    'views': views_count
                })
            except Exception as e:
                print(f"Error al extraer datos del video {i+1}: {str(e)}")
        
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
        
        # Esperar a que cargue el video con diferentes posibles elementos
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 
                    ".tiktok-1itcwxg-ImgPoster, video, div[data-e2e='browse-video'], div[data-e2e='video-container']"))
            )
        except TimeoutException:
            print(f"⚠️ Tiempo de espera agotado al cargar el video {index}. Reintentando...")
            check_for_captcha(driver)  # Verificar CAPTCHA una vez más
            time.sleep(random.uniform(5, 10))  # Esperar un poco más
        
        # Simulación de comportamiento humano
        time.sleep(random.uniform(1, 3))
        human_like_scroll(driver, random.randint(100, 300))  # Scroll suave hacia abajo
        
        # Extraer datos adicionales del video
        try:
            # Descripción del video (probando diferentes selectores)
            description = ""
            for selector in ["div[data-e2e='browse-video-desc']", "span[data-e2e='video-desc']", ".video-meta-description"]:
                try:
                    description_element = driver.find_element(By.CSS_SELECTOR, selector)
                    description = description_element.text
                    if description:
                        break
                except:
                    pass
        except:
            description = ""
        
        try:
            # Fecha de publicación (probando diferentes selectores)
            date = ""
            for selector in ["span[data-e2e='browser-nickname'] + span", "span[data-e2e='video-create-time']", ".video-meta-date"]:
                try:
                    date_element = driver.find_element(By.CSS_SELECTOR, selector)
                    date = date_element.text
                    if date:
                        break
                except:
                    pass
        except:
            date = ""
        
        try:
            # Número de likes
            likes_count = 0
            for selector in ["strong[data-e2e='like-count']", "span[data-e2e='like-count']"]:
                try:
                    likes_element = driver.find_element(By.CSS_SELECTOR, selector)
                    likes = likes_element.text
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
            for selector in ["strong[data-e2e='comment-count']", "span[data-e2e='comment-count']"]:
                try:
                    comments_element = driver.find_element(By.CSS_SELECTOR, selector)
                    comments = comments_element.text
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
                for selector in ["strong[data-e2e='video-views']", "span[data-e2e='video-views']", ".video-meta-views"]:
                    try:
                        views_element = driver.find_element(By.CSS_SELECTOR, selector)
                        views_text = views_element.text
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
        return None

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
                
                for i, (url, data) in enumerate(zip(video_urls, videos_data)):
                    # Añadir una pausa aleatoria entre cada solicitud
                    if i > 0:
                        delay = random.uniform(min_delay, max_delay)
                        print(f"Esperando {delay:.1f} segundos antes del siguiente video...")
                        time.sleep(delay)
                    
                    # Procesar el video con el driver principal
                    result = process_video(main_driver, url, data, i+1, len(video_urls))
                    if result:
                        results.append(result)
                    
                    # De vez en cuando hacer una pausa más larga para parecer humano
                    if i > 0 and i % 5 == 0:
                        long_pause = random.uniform(15, 30)
                        print(f"Haciendo una pausa más larga de {long_pause:.1f} segundos...")
                        time.sleep(long_pause)
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
        print("❌ No se encontraron videos para procesar.")
        if main_driver:
            main_driver.quit()
    
    print("\n✨ Proceso finalizado.")

if __name__ == "__main__":
    main()  