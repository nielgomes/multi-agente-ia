import re
import nltk

# Defina aqui o número mínimo de caracteres que um chunk deve ter.
TAMANHO_MINIMO_CHUNK = 300

# --- BLOCO CORRIGIDO ---
# Garante que o 'punkt' (tokenizador de sentenças) esteja disponível.
# A forma correta de verificar é tratando o LookupError.
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    print("Pacote 'punkt' do NLTK não encontrado. Baixando...")
    nltk.download('punkt', quiet=True)
    print("Download do 'punkt' concluído.")
# --- FIM DO BLOCO CORRIGIDO ---

def aplicar_formatacao_inline(texto):
    """Aplica formatação inline (`) em elementos específicos do texto."""
    texto = re.sub(r'((?<=[\s,(])(/|./)[\w./\-_]+)', r'`\1`', texto)
    texto = re.sub(r'(\$\w+)', r'`\1`', texto)
    texto = re.sub(r'(\b[A-Z_]{3,}=[\w"\./\-_]+)', r'`\1`', texto)
    return texto

def chunkificar_texto_completo(texto_completo: str) -> list[str]:
    """
    Função principal adaptada para receber um texto inteiro e retornar uma lista de chunks.
    """
    # 1. Proteger blocos de código
    code_blocks = re.findall(r'(```.*?```)', texto_completo, re.DOTALL)
    placeholders = []
    for i, block in enumerate(code_blocks):
        placeholder = f"__CODE_BLOCK_PLACEHOLDER_{i}__"
        placeholders.append(placeholder)
        texto_completo = texto_completo.replace(block, placeholder, 1)

    # 2. Lógica de Chunking
    sentencas = nltk.sent_tokenize(texto_completo, language='portuguese')
    
    chunks_finais = []
    chunk_temporario = []
    char_count_temporario = 0

    for i, sentenca in enumerate(sentencas):
        chunk_temporario.append(sentenca)
        char_count_temporario += len(sentenca)

        if char_count_temporario >= TAMANHO_MINIMO_CHUNK and sentenca.strip().endswith('.'):
            chunks_finais.append(" ".join(chunk_temporario).strip())
            chunk_temporario = []
            char_count_temporario = 0
    
    # Adiciona o último chunk se sobrou algum
    if chunk_temporario:
        chunks_finais.append(" ".join(chunk_temporario).strip())

    # 3. Restaurar blocos de código
    chunks_processados = []
    for chunk in chunks_finais:
        for i, placeholder in enumerate(placeholders):
            if placeholder in chunk:
                chunk = chunk.replace(placeholder, code_blocks[i])
        chunks_processados.append(chunk)

    # Adiciona os blocos de código originais como chunks individuais
    chunks_processados.extend(code_blocks)

    return [chunk for chunk in chunks_processados if chunk]