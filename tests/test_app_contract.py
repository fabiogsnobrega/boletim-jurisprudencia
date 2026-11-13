import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_downloads_completos_estao_dentro_da_condicao_de_usuario_autenticado():
    modulo = ast.parse((ROOT / "src" / "modules" / "jurisprudencia.py").read_text(encoding="utf-8"))
    funcao = next(node for node in modulo.body
                  if isinstance(node, ast.FunctionDef) and node.name == "render_base_tabular")
    condicoes_autenticacao = [node for node in ast.walk(funcao)
                              if isinstance(node, ast.If)
                              and isinstance(node.test, ast.Name)
                              and node.test.id == "pode_editar"]
    assert any(
        any(isinstance(chamada, ast.Call)
            and isinstance(chamada.func, ast.Attribute)
            and chamada.func.attr == "download_button"
            for statement in condicao.body for chamada in ast.walk(statement))
        for condicao in condicoes_autenticacao
    )
