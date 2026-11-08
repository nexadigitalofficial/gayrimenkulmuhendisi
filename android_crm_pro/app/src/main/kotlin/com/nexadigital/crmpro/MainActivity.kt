package com.nexadigital.crmpro

import android.Manifest
import android.annotation.SuppressLint
import android.app.DownloadManager
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.webkit.*
import android.widget.*
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout

class MainActivity : AppCompatActivity() {

    private val TAG = "NexaCRM"
    private lateinit var webView: WebView
    private lateinit var swipeRefresh: SwipeRefreshLayout
    private lateinit var progressBar: ProgressBar
    private lateinit var errorOverlay: LinearLayout
    private lateinit var txtCurrentUrl: TextView
    private lateinit var btnRetry: Button
    private lateinit var btnChangeServer: Button
    private lateinit var btnOpenDemo: Button
    private lateinit var btnFloatingConfig: FrameLayout

    private lateinit var prefs: SharedPreferences
    private var fileUploadCallback: ValueCallback<Array<Uri>>? = null

    private var backPressedTime: Long = 0
    private val PREFS_NAME = "nexa_crm_prefs"
    private val KEY_SERVER_URL = "server_url"
    private val DEFAULT_URL = "http://192.168.1.36:5000/crm"

    private val fileChooserLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        try {
            if (fileUploadCallback == null) return@registerForActivityResult
            var results: Array<Uri>? = null
            if (result.resultCode == RESULT_OK && result.data != null) {
                val data = result.data
                val dataString = data?.dataString
                val clipData = data?.clipData

                if (clipData != null) {
                    results = Array(clipData.itemCount) { i -> clipData.getItemAt(i).uri }
                } else if (dataString != null) {
                    results = arrayOf(Uri.parse(dataString))
                }
            }
            fileUploadCallback?.onReceiveValue(results)
            fileUploadCallback = null
        } catch (e: Exception) {
            Log.e(TAG, "File chooser error", e)
            fileUploadCallback?.onReceiveValue(null)
            fileUploadCallback = null
        }
    }

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { _ -> }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        try {
            setContentView(R.layout.activity_main)

            prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

            // Initialize UI Views
            webView = findViewById(R.id.webView)
            swipeRefresh = findViewById(R.id.swipeRefresh)
            progressBar = findViewById(R.id.progressBar)
            errorOverlay = findViewById(R.id.errorOverlay)
            txtCurrentUrl = findViewById(R.id.txtCurrentUrl)
            btnRetry = findViewById(R.id.btnRetry)
            btnChangeServer = findViewById(R.id.btnChangeServer)
            btnOpenDemo = findViewById(R.id.btnOpenDemo)
            btnFloatingConfig = findViewById(R.id.btnFloatingConfig)

            // Swipe Refresh Colors
            swipeRefresh.setColorSchemeColors(
                0xFFD4AF37.toInt(), // Gold
                0xFF6366F1.toInt(), // Indigo
                0xFF10B981.toInt()  // Emerald
            )
            swipeRefresh.setProgressBackgroundColorSchemeColor(0xFF0F172A.toInt())
            swipeRefresh.setOnRefreshListener {
                webView.reload()
            }

            // Configure WebView
            setupWebView()

            // Button Actions
            btnRetry.setOnClickListener {
                loadCurrentUrl()
            }

            btnChangeServer.setOnClickListener {
                showServerConfigDialog()
            }

            btnOpenDemo.setOnClickListener {
                val current = getServerUrl()
                val demoUrl = if (current.contains("?")) "$current&demo=1" else "$current?demo=1"
                saveServerUrl(demoUrl)
                loadCurrentUrl()
            }

            btnFloatingConfig.setOnClickListener {
                showServerConfigDialog()
            }

            // Handle Back Pressed
            onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
                override fun handleOnBackPressed() {
                    if (webView.canGoBack()) {
                        webView.goBack()
                    } else {
                        if (System.currentTimeMillis() - backPressedTime < 2000) {
                            finish()
                        } else {
                            backPressedTime = System.currentTimeMillis()
                            Toast.makeText(this@MainActivity, "Çıkmak için tekrar dokunun", Toast.LENGTH_SHORT).show()
                        }
                    }
                }
            })

            // Check permissions safely
            checkAppPermissions()

            // Load the configured URL
            loadCurrentUrl()

        } catch (e: Exception) {
            Log.e(TAG, "Fatal onCreate error", e)
            Toast.makeText(this, "Başlatma hatası: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        try {
            val s = webView.settings
            s.javaScriptEnabled = true
            s.domStorageEnabled = true
            s.databaseEnabled = true
            s.loadWithOverviewMode = true
            s.useWideViewPort = true
            s.allowFileAccess = true
            s.allowContentAccess = true
            s.mediaPlaybackRequiresUserGesture = false
            s.cacheMode = WebSettings.LOAD_DEFAULT
            s.setGeolocationEnabled(true)
            s.userAgentString = s.userAgentString + " NEXA-CRM-Android/1.0.0"

            webView.webChromeClient = object : WebChromeClient() {
                override fun onProgressChanged(view: WebView?, newProgress: Int) {
                    if (newProgress < 100) {
                        progressBar.visibility = View.VISIBLE
                        progressBar.progress = newProgress
                    } else {
                        progressBar.visibility = View.GONE
                    }
                }

                override fun onShowFileChooser(
                    webView: WebView?,
                    filePathCallback: ValueCallback<Array<Uri>>?,
                    fileChooserParams: FileChooserParams?
                ): Boolean {
                    fileUploadCallback?.onReceiveValue(null)
                    fileUploadCallback = filePathCallback

                    try {
                        val intent = Intent(Intent.ACTION_GET_CONTENT).apply {
                            addCategory(Intent.CATEGORY_OPENABLE)
                            type = "*/*"
                            putExtra(
                                Intent.EXTRA_MIME_TYPES,
                                arrayOf(
                                    "image/*",
                                    "application/pdf",
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                            )
                        }
                        fileChooserLauncher.launch(Intent.createChooser(intent, "Dosya Seçin"))
                        return true
                    } catch (e: Exception) {
                        Log.e(TAG, "Cannot launch file chooser", e)
                        fileUploadCallback?.onReceiveValue(null)
                        fileUploadCallback = null
                        return false
                    }
                }

                override fun onGeolocationPermissionsShowPrompt(
                    origin: String?,
                    callback: GeolocationPermissions.Callback?
                ) {
                    callback?.invoke(origin, true, false)
                }

                override fun onPermissionRequest(request: PermissionRequest?) {
                    try {
                        request?.grant(request.resources)
                    } catch (e: Exception) {
                        Log.e(TAG, "Permission request grant failed", e)
                    }
                }
            }

            webView.webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                    val url = request?.url?.toString() ?: return false
                    return handleSpecialIntents(url)
                }

                @Deprecated("Deprecated in Java")
                override fun shouldOverrideUrlLoading(view: WebView?, url: String?): Boolean {
                    if (url == null) return false
                    return handleSpecialIntents(url)
                }

                override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                    errorOverlay.visibility = View.GONE
                    swipeRefresh.isRefreshing = true
                }

                override fun onPageFinished(view: WebView?, url: String?) {
                    swipeRefresh.isRefreshing = false
                    progressBar.visibility = View.GONE
                }

                override fun onReceivedError(
                    view: WebView?,
                    request: WebResourceRequest?,
                    error: WebResourceError?
                ) {
                    if (request?.isForMainFrame == true) {
                        showErrorOverlay()
                    }
                }
            }

            // Native Download Listener for Excel exports and PDFs
            webView.setDownloadListener { url, userAgent, contentDisposition, mimetype, _ ->
                try {
                    val request = DownloadManager.Request(Uri.parse(url))
                    val filename = URLUtil.guessFileName(url, contentDisposition, mimetype)
                    request.setMimeType(mimetype)
                    request.addRequestHeader("User-Agent", userAgent)
                    request.setDescription("NEXA CRM Dosya İndiriliyor...")
                    request.setTitle(filename)
                    request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                    request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, filename)

                    val dm = getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
                    dm.enqueue(request)
                    Toast.makeText(this, "İndirme başlatıldı: $filename", Toast.LENGTH_LONG).show()
                } catch (e: Exception) {
                    Toast.makeText(this, "İndirme hatası: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error configuring webview", e)
        }
    }

    private fun handleSpecialIntents(url: String): Boolean {
        return try {
            when {
                url.startsWith("tel:") -> {
                    val intent = Intent(Intent.ACTION_DIAL, Uri.parse(url))
                    startActivity(intent)
                    true
                }
                url.startsWith("whatsapp:") || url.contains("api.whatsapp.com") || url.contains("wa.me") -> {
                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                    startActivity(intent)
                    true
                }
                url.startsWith("mailto:") -> {
                    val intent = Intent(Intent.ACTION_SENDTO, Uri.parse(url))
                    startActivity(intent)
                    true
                }
                url.startsWith("geo:") || url.contains("maps.google.com") -> {
                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                    startActivity(intent)
                    true
                }
                else -> false
            }
        } catch (e: Exception) {
            Toast.makeText(this, "Uygulama açılamadı: ${e.message}", Toast.LENGTH_SHORT).show()
            false
        }
    }

    private fun showErrorOverlay() {
        val currentUrl = getServerUrl()
        txtCurrentUrl.text = currentUrl
        errorOverlay.visibility = View.VISIBLE
        swipeRefresh.isRefreshing = false
        progressBar.visibility = View.GONE
    }

    private fun loadCurrentUrl() {
        try {
            val url = getServerUrl()
            errorOverlay.visibility = View.GONE
            webView.loadUrl(url)
        } catch (e: Exception) {
            Log.e(TAG, "Error loading url", e)
            showErrorOverlay()
        }
    }

    private fun getServerUrl(): String {
        return prefs.getString(KEY_SERVER_URL, DEFAULT_URL) ?: DEFAULT_URL
    }

    private fun saveServerUrl(url: String) {
        prefs.edit().putString(KEY_SERVER_URL, url.trim()).apply()
    }

    private fun showServerConfigDialog() {
        try {
            val dialogView = LayoutInflater.from(this).inflate(R.layout.dialog_server_config, null)
            val editUrl = dialogView.findViewById<EditText>(R.id.editServerUrl)
            val chipLocal = dialogView.findViewById<Button>(R.id.chipLocal)
            val chipDemo = dialogView.findViewById<Button>(R.id.chipDemo)
            val chipEmulator = dialogView.findViewById<Button>(R.id.chipEmulator)
            val btnClearCache = dialogView.findViewById<Button>(R.id.btnClearCache)
            val btnCancel = dialogView.findViewById<Button>(R.id.btnCancel)
            val btnSave = dialogView.findViewById<Button>(R.id.btnSaveConfig)

            editUrl.setText(getServerUrl())

            val dialog = AlertDialog.Builder(this)
                .setView(dialogView)
                .create()

            dialog.window?.setBackgroundDrawableResource(android.R.color.transparent)

            chipLocal.setOnClickListener {
                editUrl.setText("http://192.168.1.36:5000/crm")
            }

            chipDemo.setOnClickListener {
                editUrl.setText("http://192.168.1.36:5000/crm?demo=1")
            }

            chipEmulator.setOnClickListener {
                editUrl.setText("http://10.0.2.2:5000/crm")
            }

            btnClearCache.setOnClickListener {
                webView.clearCache(true)
                CookieManager.getInstance().removeAllCookies(null)
                Toast.makeText(this, "Önbellek ve çerezler temizlendi", Toast.LENGTH_SHORT).show()
            }

            btnCancel.setOnClickListener {
                dialog.dismiss()
            }

            btnSave.setOnClickListener {
                val newUrl = editUrl.text.toString().trim()
                if (newUrl.isNotEmpty()) {
                    saveServerUrl(newUrl)
                    dialog.dismiss()
                    loadCurrentUrl()
                    Toast.makeText(this, "Bağlanılıyor: $newUrl", Toast.LENGTH_SHORT).show()
                }
            }

            dialog.show()
        } catch (e: Exception) {
            Log.e(TAG, "Error opening dialog", e)
        }
    }

    private fun checkAppPermissions() {
        try {
            val permissions = mutableListOf(
                Manifest.permission.CAMERA,
                Manifest.permission.RECORD_AUDIO,
                Manifest.permission.ACCESS_FINE_LOCATION,
                Manifest.permission.ACCESS_COARSE_LOCATION
            )
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                permissions.add(Manifest.permission.READ_MEDIA_IMAGES)
                permissions.add(Manifest.permission.READ_MEDIA_AUDIO)
                permissions.add(Manifest.permission.POST_NOTIFICATIONS)
            } else {
                permissions.add(Manifest.permission.READ_EXTERNAL_STORAGE)
            }

            val needed = permissions.filter {
                ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
            }
            if (needed.isNotEmpty()) {
                requestPermissionLauncher.launch(needed.toTypedArray())
            }
        } catch (e: Exception) {
            Log.w(TAG, "Permissions check warning: ${e.message}")
        }
    }
}
