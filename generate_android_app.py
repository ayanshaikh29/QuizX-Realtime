import os
import pathlib

def create_file(path, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')

base_dir = r"c:\Users\HP\Desktop\QuizXApp"

# --- Gradle & Project Root Files ---
create_file(f"{base_dir}/settings.gradle.kts", """
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "QuizX"
include(":app")
""")

create_file(f"{base_dir}/build.gradle.kts", """
buildscript {
    repositories {
        google()
        mavenCentral()
    }
    dependencies {
        classpath("com.android.tools.build:gradle:8.2.2")
        classpath("org.jetbrains.kotlin:kotlin-gradle-plugin:1.9.22")
    }
}
plugins {
    id("com.android.application") version "8.2.2" apply false
    id("org.jetbrains.kotlin.android") version "1.9.22" apply false
}
""")

create_file(f"{base_dir}/gradle.properties", """
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
android.useAndroidX=true
kotlin.code.style=official
android.nonTransitiveRClass=true
""")

# --- App Module Gradle ---
create_file(f"{base_dir}/app/build.gradle.kts", """
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.quizx.app"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.quizx.app"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }
    kotlinOptions {
        jvmTarget = "1.8"
    }
    buildFeatures {
        viewBinding = true
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.11.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.swiperefreshlayout:swiperefreshlayout:1.1.0")
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.5.1")
}
""")

# --- AndroidManifest.xml ---
create_file(f"{base_dir}/app/src/main/AndroidManifest.xml", """
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:tools="http://schemas.android.com/tools">

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

    <application
        android:allowBackup="true"
        android:dataExtractionRules="@xml/data_extraction_rules"
        android:fullBackupContent="@xml/backup_rules"
        android:icon="@mipmap/ic_launcher"
        android:label="QuizX"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:supportsRtl="true"
        android:theme="@style/Theme.QuizX"
        android:usesCleartextTraffic="true"
        tools:targetApi="31">
        
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:theme="@style/Theme.QuizX.NoActionBar"
            android:configChanges="orientation|keyboardHidden|screenSize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>

</manifest>
""")

# --- Resource Files (res/) ---
create_file(f"{base_dir}/app/src/main/res/values/colors.xml", """
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="primary">#10b981</color>
    <color name="primary_dark">#059669</color>
    <color name="accent">#c5f82a</color>
    <color name="black">#FF000000</color>
    <color name="white">#FFFFFFFF</color>
    <color name="background">#f8fafc</color>
    <color name="text_main">#111827</color>
    <color name="text_muted">#6b7280</color>
</resources>
""")

create_file(f"{base_dir}/app/src/main/res/values/themes.xml", """
<resources xmlns:tools="http://schemas.android.com/tools">
    <style name="Theme.QuizX" parent="Theme.MaterialComponents.DayNight.DarkActionBar">
        <item name="colorPrimary">@color/primary</item>
        <item name="colorPrimaryVariant">@color/primary_dark</item>
        <item name="colorOnPrimary">@color/white</item>
        <item name="colorSecondary">@color/accent</item>
        <item name="colorSecondaryVariant">@color/accent</item>
        <item name="colorOnSecondary">@color/black</item>
        <item name="android:statusBarColor">?attr/colorPrimaryVariant</item>
    </style>

    <style name="Theme.QuizX.NoActionBar">
        <item name="windowActionBar">false</item>
        <item name="windowNoTitle">true</item>
        <item name="android:statusBarColor">@color/primary_dark</item>
    </style>
</resources>
""")

# --- Layout Files ---
create_file(f"{base_dir}/app/src/main/res/layout/activity_main.xml", """
<?xml version="1.0" encoding="utf-8"?>
<androidx.constraintlayout.widget.ConstraintLayout xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    xmlns:tools="http://schemas.android.com/tools"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:background="@color/white"
    tools:context=".MainActivity">

    <androidx.swiperefreshlayout.widget.SwipeRefreshLayout
        android:id="@+id/swipeRefreshLayout"
        android:layout_width="match_parent"
        android:layout_height="match_parent">

        <WebView
            android:id="@+id/webView"
            android:layout_width="match_parent"
            android:layout_height="match_parent" />

    </androidx.swiperefreshlayout.widget.SwipeRefreshLayout>

    <ProgressBar
        android:id="@+id/progressBar"
        style="?android:attr/progressBarStyleHorizontal"
        android:layout_width="match_parent"
        android:layout_height="4dp"
        android:indeterminate="true"
        android:visibility="gone"
        app:layout_constraintTop_toTopOf="parent" />

    <include
        android:id="@+id/errorLayout"
        layout="@layout/layout_error"
        android:visibility="gone" />

    <include
        android:id="@+id/splashLayout"
        layout="@layout/layout_splash"
        android:visibility="visible" />

</androidx.constraintlayout.widget.ConstraintLayout>
""")

create_file(f"{base_dir}/app/src/main/res/layout/layout_error.xml", """
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:background="@color/background"
    android:gravity="center"
    android:orientation="vertical"
    android:padding="32dp">

    <ImageView
        android:layout_width="120dp"
        android:layout_height="120dp"
        android:src="@android:drawable/ic_dialog_alert"
        app:tint="@color/text_muted"
        xmlns:app="http://schemas.android.com/apk/res-auto" />

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:layout_marginTop="24dp"
        android:text="Connection Lost"
        android:textColor="@color/text_main"
        android:textSize="24sp"
        android:textStyle="bold" />

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:layout_marginTop="8dp"
        android:gravity="center"
        android:text="Unable to connect to the QuizX server.\\nPlease check your internet connection."
        android:textColor="@color/text_muted"
        android:textSize="16sp" />

    <Button
        android:id="@+id/btnRetry"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:layout_marginTop="32dp"
        android:backgroundTint="@color/primary"
        android:paddingHorizontal="32dp"
        android:paddingVertical="12dp"
        android:text="Try Again"
        android:textColor="@color/white" />

</LinearLayout>
""")

create_file(f"{base_dir}/app/src/main/res/layout/layout_splash.xml", """
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:background="@color/white"
    android:gravity="center"
    android:orientation="vertical">

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="QuizX"
        android:textColor="@color/primary"
        android:textSize="48sp"
        android:textStyle="bold" />

    <ProgressBar
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:layout_marginTop="32dp"
        android:indeterminateTint="@color/primary" />

</LinearLayout>
""")

create_file(f"{base_dir}/app/src/main/res/xml/backup_rules.xml", """
<?xml version="1.0" encoding="utf-8"?>
<full-backup-content>
    <include domain="sharedpref" path="."/>
</full-backup-content>
""")

create_file(f"{base_dir}/app/src/main/res/xml/data_extraction_rules.xml", """
<?xml version="1.0" encoding="utf-8"?>
<data-extraction-rules>
    <cloud-backup>
        <include domain="sharedpref" path="."/>
    </cloud-backup>
    <device-transfer>
        <include domain="sharedpref" path="."/>
    </device-transfer>
</data-extraction-rules>
""")

# --- Kotlin Source Code ---
kt_dir = f"{base_dir}/app/src/main/java/com/quizx/app"

create_file(f"{kt_dir}/Config.kt", """
package com.quizx.app

object Config {
    // IMPORTANT: Change this to your Flask backend IP address
    // Make sure your phone and PC are on the same Wi-Fi network
    const val BASE_URL = "http://192.168.1.5:5000"
}
""")

create_file(f"{kt_dir}/MainActivity.kt", """
package com.quizx.app

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Bitmap
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Bundle
import android.view.View
import android.webkit.CookieManager
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import androidx.appcompat.app.AppCompatActivity
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var swipeRefreshLayout: SwipeRefreshLayout
    private lateinit var errorLayout: View
    private lateinit var splashLayout: View
    private lateinit var btnRetry: Button
    private lateinit var progressBar: View

    private var isError = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webView)
        swipeRefreshLayout = findViewById(R.id.swipeRefreshLayout)
        errorLayout = findViewById(R.id.errorLayout)
        splashLayout = findViewById(R.id.splashLayout)
        btnRetry = findViewById(R.id.btnRetry)
        progressBar = findViewById(R.id.progressBar)

        setupWebView()

        swipeRefreshLayout.setOnRefreshListener {
            if (isNetworkAvailable()) {
                hideError()
                webView.reload()
            } else {
                swipeRefreshLayout.isRefreshing = false
                showError()
            }
        }

        btnRetry.setOnClickListener {
            if (isNetworkAvailable()) {
                hideError()
                webView.loadUrl(Config.BASE_URL)
            }
        }

        // Initial Load
        if (isNetworkAvailable()) {
            webView.loadUrl(Config.BASE_URL)
        } else {
            splashLayout.visibility = View.GONE
            showError()
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        val settings = webView.settings
        
        // Essential for Socket.IO and Web functionality
        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.databaseEnabled = true
        
        // Helpful defaults
        settings.useWideViewPort = true
        settings.loadWithOverviewMode = true
        settings.loadsImagesAutomatically = true
        settings.mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
        
        // Prevent zoom for app-like feel
        settings.setSupportZoom(false)
        settings.builtInZoomControls = false
        settings.displayZoomControls = false

        // Keep sessions persistent
        CookieManager.getInstance().setAcceptCookie(true)
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true)

        webView.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                if (newProgress < 100) {
                    progressBar.visibility = View.VISIBLE
                } else {
                    progressBar.visibility = View.GONE
                }
            }
        }

        webView.webViewClient = object : WebViewClient() {
            
            override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                super.onPageStarted(view, url, favicon)
                isError = false
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                swipeRefreshLayout.isRefreshing = false
                
                // Hide splash screen on first successful load
                if (!isError && splashLayout.visibility == View.VISIBLE) {
                    splashLayout.visibility = View.GONE
                }
            }

            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?
            ) {
                super.onReceivedError(view, request, error)
                if (request?.isForMainFrame == true) {
                    isError = true
                    showError()
                }
            }
        }
    }

    private fun showError() {
        webView.visibility = View.GONE
        splashLayout.visibility = View.GONE
        errorLayout.visibility = View.VISIBLE
    }

    private fun hideError() {
        errorLayout.visibility = View.GONE
        webView.visibility = View.VISIBLE
    }

    private fun isNetworkAvailable(): Boolean {
        val connectivityManager = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val network = connectivityManager.activeNetwork ?: return false
        val activeNetwork = connectivityManager.getNetworkCapabilities(network) ?: return false
        
        return when {
            activeNetwork.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) -> true
            activeNetwork.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) -> true
            activeNetwork.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET) -> true
            else -> false
        }
    }

    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }
}
""")

print("QuizXApp generated successfully at: " + base_dir)
