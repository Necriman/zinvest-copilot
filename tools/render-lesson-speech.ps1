$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$zinvestVoiceDir = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../redesign-assets/voice'))
$zinvestPhrases = Get-Content -LiteralPath (Join-Path $zinvestVoiceDir 'phrases.json') -Raw | ConvertFrom-Json
$zinvestSynth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
  $zinvestSynth.SelectVoice('Microsoft Pavel')
  $zinvestSynth.Rate = 0
  $zinvestFormat = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(22050, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
  foreach ($zinvestPhrase in $zinvestPhrases) {
    $zinvestWave = Join-Path $zinvestVoiceDir ('phrase-' + $zinvestPhrase.id + '.wav')
    $zinvestSynth.SetOutputToWaveFile($zinvestWave, $zinvestFormat)
    $zinvestSynth.Speak([string]$zinvestPhrase.text)
    $zinvestSynth.SetOutputToNull()
  }
  Write-Output ('Rendered ' + $zinvestPhrases.Count + ' Russian phrases with Microsoft Pavel.')
} finally { $zinvestSynth.Dispose() }
