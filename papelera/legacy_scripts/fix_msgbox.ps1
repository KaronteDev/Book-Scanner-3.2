# Script PowerShell para convertir messagebox a Messagebox con fallback

param(
    [string]$FilePath
)

$content = Get-Content $FilePath -Raw -Encoding UTF8

# Función para convertir una línea con messagebox
function Convert-MessageBoxLine {
    param([string]$Line, [string]$Method, [string]$NewMethod)
    
    if ($Line -match "messagebox\.$Method\(") {
        # Extraer indentación
        $indent = ($Line -match '^(\s*)') ? $Matches[1] : ''
        
        # Reemplazar el método
        $newLine = $Line -replace "messagebox\.$Method\(", "XXX_PLACEHOLDER_XXX("
        
        # Crear las líneas con fallback
        $result = "${indent}if Messagebox:`n"
        $result += "${indent}    " + ($newLine -replace 'XXX_PLACEHOLDER_XXX', "Messagebox.$NewMethod") -replace '\)(\s*)$', ', parent=self.root)$1'
        $result += "`n${indent}else:`n"
        $result += "${indent}    " + ($Line.TrimStart())
        
        return $result
    }
    return $Line
}

# Patrones de reemplazo
$patterns = @{
    'showerror' = 'show_error'
    'showinfo' = 'show_info'
    'showwarning' = 'show_warning'
}

# Procesar línea por línea
$lines = $content -split "`n"
$newLines = @()

foreach ($line in $lines) {
    $processed = $false
    foreach ($old in $patterns.Keys) {
        if ($line -match "^\s*messagebox\.$old\(" -and $line -notmatch '^\s*if') {
            $newLines += Convert-MessageBoxLine $line $old $patterns[$old]
            $processed = $true
            break
        }
    }
    
    # Caso especial para askyesno en if statements
    if ($line -match '^\s*if.*messagebox\.askyesno\(') {
        $indent = ($line -match '^(\s*)') ? $Matches[1] : ''
        $ifPart = $line -replace 'messagebox\.askyesno\(([^)]+)\)', '(Messagebox.yesno($1, parent=self.root) if Messagebox else messagebox.askyesno($1))'
        $newLines += $ifPart
        $processed = $true
    }
    
    if (-not $processed) {
        $newLines += $line
    }
}

$newContent = $newLines -join "`n"
Set-Content $FilePath -Value $newContent -Encoding UTF8 -NoNewline

Write-Host "✓ Procesado: $FilePath"
