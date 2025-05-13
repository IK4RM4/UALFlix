#!/usr/bin/env python3
import subprocess
import time
import os
import sys
import argparse
import json
import requests
from concurrent.futures import ThreadPoolExecutor

# Configuração dos testes
DEFAULT_USERS = 50
DEFAULT_DURATION = 60  # segundos
DEFAULT_RAMP_UP = 10  # segundos

# URL base do sistema
BASE_URL = "http://localhost"

# Endpoints para teste
ENDPOINTS = {
    "list_videos": "/api/videos",
    "upload_video": "/api/upload",
    "stream_video": "/videos/sample.mp4"  # Substitua por um vídeo real do seu sistema
}

# Arquivo de vídeo de exemplo para upload
SAMPLE_VIDEO = "sample/test_video.mp4"

def make_request(endpoint, method="GET", data=None, files=None):
    """Faz uma requisição HTTP e retorna o tempo de resposta."""
    url = f"{BASE_URL}{endpoint}"
    start_time = time.time()
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, data=data, files=files, timeout=30)
        
        end_time = time.time()
        response_time = end_time - start_time
        
        return {
            "url": url,
            "method": method,
            "status_code": response.status_code,
            "response_time": response_time,
            "success": 200 <= response.status_code < 300
        }
    except Exception as e:
        end_time = time.time()
        return {
            "url": url,
            "method": method,
            "status_code": 0,
            "response_time": end_time - start_time,
            "success": False,
            "error": str(e)
        }

def simulate_user(user_id, duration, results):
    """Simula o comportamento de um usuário por um período de tempo."""
    start_time = time.time()
    end_time = start_time + duration
    user_results = []
    
    while time.time() < end_time:
        # Listar vídeos (70% das requisições)
        if time.time() % 10 < 7:
            result = make_request(ENDPOINTS["list_videos"])
            user_results.append(result)
        
        # Fazer streaming de um vídeo (25% das requisições)
        elif time.time() % 10 < 9.5:
            result = make_request(ENDPOINTS["stream_video"])
            user_results.append(result)
        
        # Fazer upload de um vídeo (5% das requisições)
        else:
            if os.path.exists(SAMPLE_VIDEO):
                files = {'file': open(SAMPLE_VIDEO, 'rb')}
                data = {
                    'title': f'Test Video {user_id}',
                    'description': f'Uploaded by load test user {user_id}'
                }
                result = make_request(ENDPOINTS["upload_video"], method="POST", data=data, files=files)
                user_results.append(result)
                files['file'].close()
            else:
                print(f"Arquivo de vídeo de exemplo não encontrado: {SAMPLE_VIDEO}")
        
        # Pausa pequena entre requisições
        time.sleep(0.5)
    
    results.extend(user_results)

def run_load_test(users, duration, ramp_up):
    """Executa um teste de carga com um número específico de usuários simultâneos."""
    print(f"Iniciando teste de carga com {users} usuários por {duration} segundos (ramp-up de {ramp_up} segundos)...")
    
    results = []
    
    with ThreadPoolExecutor(max_workers=users) as executor:
        # Distribuir o início dos usuários durante o período de ramp-up
        for i in range(users):
            # Calcula o tempo de espera para iniciar este usuário
            if ramp_up > 0 and users > 1:
                wait_time = (i * ramp_up) / (users - 1)
            else:
                wait_time = 0
                
            time.sleep(wait_time)
            print(f"Iniciando usuário {i+1}/{users}")
            executor.submit(simulate_user, i+1, duration, results)
    
    print("Teste de carga concluído!")
    
    return results

def analyze_results(results):
    """Analisa os resultados do teste de carga."""
    if not results:
        print("Nenhum resultado para analisar.")
        return
    
    total_requests = len(results)
    successful_requests = sum(1 for r in results if r["success"])
    failed_requests = total_requests - successful_requests
    
    response_times = [r["response_time"] for r in results]
    avg_response_time = sum(response_times) / len(response_times)
    max_response_time = max(response_times)
    min_response_time = min(response_times)
    
    # Cálculo de percentis
    response_times.sort()
    p50 = response_times[int(total_requests * 0.5)]
    p90 = response_times[int(total_requests * 0.9)]
    p95 = response_times[int(total_requests * 0.95)]
    p99 = response_times[int(total_requests * 0.99)]
    
    # Agrupar por endpoint
    endpoints = {}
    for r in results:
        endpoint = r["url"].replace(BASE_URL, "")
        if endpoint not in endpoints:
            endpoints[endpoint] = {"total": 0, "success": 0, "times": []}
        endpoints[endpoint]["total"] += 1
        endpoints[endpoint]["success"] += 1 if r["success"] else 0
        endpoints[endpoint]["times"].append(r["response_time"])
    
    # Calcular estatísticas por endpoint
    for endpoint, data in endpoints.items():
        data["success_rate"] = (data["success"] / data["total"]) * 100
        data["avg_time"] = sum(data["times"]) / len(data["times"])
        data["min_time"] = min(data["times"])
        data["max_time"] = max(data["times"])
        data["p95_time"] = sorted(data["times"])[int(len(data["times"]) * 0.95)]
    
    # Imprimir resultados
    print("\n===== RESULTADOS DO TESTE DE CARGA =====")
    print(f"Total de requisições: {total_requests}")
    print(f"Requisições bem-sucedidas: {successful_requests} ({(successful_requests/total_requests)*100:.2f}%)")
    print(f"Requisições falhas: {failed_requests} ({(failed_requests/total_requests)*100:.2f}%)")
    print(f"Tempo médio de resposta: {avg_response_time:.4f} segundos")
    print(f"Tempo máximo de resposta: {max_response_time:.4f} segundos")
    print(f"Tempo mínimo de resposta: {min_response_time:.4f} segundos")
    print(f"P50 (mediana): {p50:.4f} segundos")
    print(f"P90: {p90:.4f} segundos")
    print(f"P95: {p95:.4f} segundos")
    print(f"P99: {p99:.4f} segundos")
    
    print("\n===== ESTATÍSTICAS POR ENDPOINT =====")
    for endpoint, data in endpoints.items():
        print(f"\nEndpoint: {endpoint}")
        print(f"Total de requisições: {data['total']}")
        print(f"Taxa de sucesso: {data['success_rate']:.2f}%")
        print(f"Tempo médio: {data['avg_time']:.4f} segundos")
        print(f"Tempo mínimo: {data['min_time']:.4f} segundos")
        print(f"Tempo máximo: {data['max_time']:.4f} segundos")
        print(f"P95: {data['p95_time']:.4f} segundos")
    
    # Salvar resultados em um arquivo
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"load_test_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "summary": {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "success_rate": (successful_requests/total_requests)*100,
                "avg_response_time": avg_response_time,
                "max_response_time": max_response_time,
                "min_response_time": min_response_time,
                "p50": p50,
                "p90": p90,
                "p95": p95,
                "p99": p99
            },
            "endpoints": endpoints,
            "raw_results": results
        }, f, indent=2)
    
    print(f"\nResultados detalhados salvos em: {filename}")

def main():
    parser = argparse.ArgumentParser(description='Executa testes de carga no UALFlix.')
    parser.add_argument('-u', '--users', type=int, default=DEFAULT_USERS,
                        help=f'Número de usuários simultâneos (padrão: {DEFAULT_USERS})')
    parser.add_argument('-d', '--duration', type=int, default=DEFAULT_DURATION,
                        help=f'Duração do teste em segundos (padrão: {DEFAULT_DURATION})')
    parser.add_argument('-r', '--ramp-up', type=int, default=DEFAULT_RAMP_UP,
                        help=f'Tempo de rampa em segundos (padrão: {DEFAULT_RAMP_UP})')
    
    args = parser.parse_args()
    
    # Criar diretório para o vídeo de exemplo se não existir
    os.makedirs(os.path.dirname(SAMPLE_VIDEO), exist_ok=True)
    
    # Verificar se o vídeo de exemplo existe, caso contrário criar um
    if not os.path.exists(SAMPLE_VIDEO):
        print(f"Criando vídeo de teste em {SAMPLE_VIDEO}...")
        try:
            # Cria um vídeo de teste usando ffmpeg
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", "testsrc=duration=5:size=640x360:rate=30",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                SAMPLE_VIDEO
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("Vídeo de teste criado com sucesso!")
        except Exception as e:
            print(f"Erro ao criar vídeo de teste: {e}")
            print("Por favor, crie manualmente um vídeo de teste.")
            sys.exit(1)
    
    # Executar teste de carga
    results = run_load_test(args.users, args.duration, args.ramp_up)
    
    # Analisar resultados
    analyze_results(results)

if __name__ == "__main__":
    main()