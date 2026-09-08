param(
    [string]$InstallRoot = 'D:\Qwen3-ASR',
    [string]$PythonExe = 'python',
    [ValidateSet('1.7B', '0.6B')]
    [string]$ModelSize = '0.6B'
)

$ErrorActionPreference = 'Stop'

$tempRoot = Join-Path $InstallRoot 'tmp'
$pipCache = Join-Path $InstallRoot 'cache\pip'
$hfCache = Join-Path $InstallRoot 'cache\huggingface'
$torchCache = Join-Path $InstallRoot 'cache\torch'
$envRoot = Join-Path $InstallRoot 'env'
$modelRoot = Join-Path $InstallRoot "models\Qwen3-ASR-$ModelSize"

New-Item -ItemType Directory -Force -Path $InstallRoot, $tempRoot, $pipCache, $hfCache, $torchCache, (Join-Path $InstallRoot 'outputs') | Out-Null

$env:TEMP = $tempRoot
$env:TMP = $tempRoot
$env:PIP_CACHE_DIR = $pipCache
$env:HF_HOME = $hfCache
$env:HUGGINGFACE_HUB_CACHE = Join-Path $hfCache 'hub'
$env:TORCH_HOME = $torchCache

if (-not (Test-Path -LiteralPath (Join-Path $envRoot 'Scripts\python.exe'))) {
    & $PythonExe -m venv $envRoot
}

$venvPython = Join-Path $envRoot 'Scripts\python.exe'
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install --no-deps 'qwen-asr==0.0.6'
& $venvPython -m pip install 'torch==2.9.1' 'torchaudio==2.9.1' --index-url 'https://download.pytorch.org/whl/cu128'
& $venvPython -m pip install 'transformers==4.57.6' 'accelerate==1.12.0' 'qwen-omni-utils' 'librosa' 'soundfile' 'nagisa==0.2.11' 'soynlp==0.0.493' 'sox'

$hfExe = Join-Path $envRoot 'Scripts\hf.exe'
& $hfExe download "Qwen/Qwen3-ASR-$ModelSize" --local-dir $modelRoot

& $venvPython -c "import torch; from qwen_asr import Qwen3ASRModel; assert torch.cuda.is_available(); print(torch.cuda.get_device_name(0))"
Write-Output "Deployment ready: $InstallRoot"
