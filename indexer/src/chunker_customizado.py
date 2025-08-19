#indexer/src/chunker_customizado.py
import re
import nltk

# Defina aqui o número mínimo de caracteres que um chunk deve ter.
TAMANHO_MINIMO_CHUNK = 600
# Chunk Overlap - Número de SENTENÇAS que o final de um chunk irá compartilhar com o início do próximo.
SOBREPOSICAO_EM_SENTENCAS = 3

# Garante que o 'punkt' (tokenizador de sentenças) esteja disponível.
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    print("Pacote 'punkt' do NLTK não encontrado. Baixando...")
    nltk.download('punkt', quiet=True)
    print("Download do 'punkt' concluído.")

def aplicar_formatacao_inline(texto):
    """Aplica formatação inline (`) em elementos específicos do texto."""
    texto = re.sub(r'((?<=[\s,(])(/|./)[\w./\-_]+)', r'`\1`', texto)
    texto = re.sub(r'(\$\w+)', r'`\1`', texto)
    texto = re.sub(r'(\b[A-Z_]{3,}=[\w"\./\-_]+)', r'`\1`', texto)
    return texto

def chunkificar_texto_completo(texto_completo: str) -> list[str]:
    """
    Função principal refatorada para aplicar sobreposição (overlap) de sentenças entre os chunks.
    """
    # 1. Proteger blocos de código
    code_blocks = re.findall(r'(```.*?```)', texto_completo, re.DOTALL)
    placeholders = []
    for i, block in enumerate(code_blocks):
        placeholder = f"__CODE_BLOCK_PLACEHOLDER_{i}__"
        placeholders.append(placeholder)
        texto_completo = texto_completo.replace(block, placeholder, 1)

    # 2. Lógica de Chunking Refatorada com Sobreposição
    sentencas = nltk.sent_tokenize(texto_completo, language='portuguese')

    if not sentencas:
        return []

    chunks_finais = []
    indice_inicio_chunk_atual = 0

    while indice_inicio_chunk_atual < len(sentencas):
        chunk_temporario = []
        char_count_temporario = 0
        
        # Constrói um chunk até atingir o tamanho mínimo
        for i in range(indice_inicio_chunk_atual, len(sentencas)):
            sentenca = sentencas[i]
            chunk_temporario.append(sentenca)
            char_count_temporario += len(sentenca)
            
            # Condição para finalizar o chunk
            if char_count_temporario >= TAMANHO_MINIMO_CHUNK:
                break
        
        # Adiciona o chunk construído à lista final
        chunks_finais.append(" ".join(chunk_temporario).strip())
        
        # --- LÓGICA DA SOBREPOSIÇÃO ---
        # Calcula o ponto de partida do PRÓXIMO chunk.
        # Em vez de começar da próxima sentença (i + 1), ele "volta atrás"
        # algumas sentenças para criar a sobreposição.
        indice_proximo_chunk = i + 1
        
        # O novo ponto de partida é o final do chunk atual menos a sobreposição.
        # Garantimos que não seja um índice negativo.
        indice_inicio_proximo_chunk = max(indice_inicio_chunk_atual + 1, indice_proximo_chunk - SOBREPOSICAO_EM_SENTENCAS)

        # Se o próximo chunk começaria depois do final da lista, paramos o loop.
        if indice_inicio_proximo_chunk >= len(sentencas):
            break
            
        indice_inicio_chunk_atual = indice_inicio_proximo_chunk

    # 3. Restaurar blocos de código (lógica inalterada)
    chunks_processados = []
    for chunk in chunks_finais:
        for i, placeholder in enumerate(placeholders):
            if placeholder in chunk:
                chunk = chunk.replace(placeholder, code_blocks[i])
        chunks_processados.append(chunk)

    # Adiciona os blocos de código originais como chunks individuais
    chunks_processados.extend(code_blocks)

    return [chunk for chunk in chunks_processados if chunk]