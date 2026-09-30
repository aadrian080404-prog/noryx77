package com.noryx.jarvis

/** Device-side contract only: Android permission/audio code belongs in the client. */
interface AudioWakeBridge {
    fun start(onPcmFrame: (ByteArray, Long, Int) -> Unit)
    fun stop()
}
