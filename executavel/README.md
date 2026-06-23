# Executável do Cassol PreCalc

## Gerar

Execute na raiz do projeto:

```powershell
py -m pip install pyinstaller
py -m PyInstaller --noconfirm --clean executavel/CassolPreCalc.spec
```

O resultado será criado em `dist/CassolPreCalc/CassolPreCalc.exe`. A pasta inteira
`dist/CassolPreCalc` deve ser distribuída; o `.exe` depende do conteúdo de `_internal`.

## Usar

1. Abra `CassolPreCalc.exe`.
2. Mantenha a janela do terminal aberta enquanto estiver usando o app.
3. O navegador será aberto automaticamente.
4. Para encerrar completamente, feche o terminal ou pressione `Ctrl+C`.

O computador de destino não precisa ter Python instalado.
