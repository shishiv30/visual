package local.visual.corepose

import android.app.DatePickerDialog
import android.Manifest
import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.SurfaceTexture
import android.media.MediaMetadataRetriever
import android.media.MediaPlayer
import android.media.PlaybackParams
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.util.Log
import android.view.LayoutInflater
import android.view.Surface
import android.view.TextureView
import android.view.View
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.EditText
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.PopupMenu
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import androidx.core.content.FileProvider
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.CameraSelector
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.video.FileOutputOptions
import androidx.camera.video.Quality
import androidx.camera.video.QualitySelector
import androidx.camera.video.Recorder
import androidx.camera.video.Recording
import androidx.camera.video.FallbackStrategy
import androidx.camera.video.VideoCapture
import androidx.camera.video.VideoRecordEvent
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import com.google.android.material.button.MaterialButton
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.math.max
import kotlin.math.roundToInt

class MainActivity : AppCompatActivity() {
    private lateinit var library: Library
    private lateinit var ingest: Ingest
    private lateinit var engine: PoseEngine
    private lateinit var athletes: Athletes
    private val cameraExecutor: ExecutorService = Executors.newSingleThreadExecutor()
    private val overlayHandler = Handler(Looper.getMainLooper())
    private val recordHandler = Handler(Looper.getMainLooper())
    private val analyzing = AtomicBoolean(false)

    private lateinit var pageList: View
    private lateinit var pageCapture: View
    private lateinit var pagePrepare: View
    private lateinit var pagePlayer: View
    private lateinit var loading: View
    private lateinit var loadingCaption: TextView
    private lateinit var clipList: LinearLayout
    private lateinit var btnCamera: MaterialButton
    private lateinit var btnImport: MaterialButton
    private lateinit var labelLanguage: TextView
    private lateinit var spinnerLanguage: Spinner

    private lateinit var capturePreview: PreviewView
    private lateinit var captureHint: TextView
    private lateinit var captureDenied: View
    private lateinit var captureDeniedTitle: TextView
    private lateinit var captureDeniedBody: TextView
    private lateinit var btnAllowCamera: MaterialButton
    private lateinit var btnRecord: MaterialButton
    private lateinit var btnCaptureImport: MaterialButton
    private lateinit var btnCaptureBack: ImageButton

    private lateinit var prepareCanvas: SeedCanvasView
    private lateinit var prepareTime: TextView
    private lateinit var prepareTimeline: TimelineStripView
    private lateinit var prepareRange: TextView
    private lateinit var btnStartAnalysis: MaterialButton
    private lateinit var btnPrepareBack: ImageButton
    private lateinit var labelProfile: TextView
    private lateinit var labelName: TextView
    private lateinit var labelBirthday: TextView
    private lateinit var labelHeight: TextView
    private lateinit var labelGender: TextView
    private lateinit var labelWeight: TextView
    private lateinit var labelSki: TextView
    private lateinit var unitHeight: TextView
    private lateinit var unitWeight: TextView
    private lateinit var unitSki: TextView
    private lateinit var spinnerProfile: Spinner
    private lateinit var spinnerGender: Spinner
    private lateinit var inputName: EditText
    private lateinit var inputBirthday: TextView
    private lateinit var inputHeight: EditText
    private lateinit var inputWeight: EditText
    private lateinit var inputSki: EditText

    private lateinit var playerStage: PlayerStageView
    private lateinit var playerVideo: TextureView
    private lateinit var playerImage: ImageView
    private lateinit var playerOverlay: PoseOverlayView
    private lateinit var playerChrome: View
    private lateinit var playerTimeline: TimelineStripView
    private lateinit var playerReport: ReportPanelView
    private lateinit var btnPlay: MaterialButton
    private lateinit var btnLocator: MaterialButton
    private lateinit var btnSpeed: MaterialButton
    private lateinit var btnLike: MaterialButton
    private lateinit var btnUnlike: MaterialButton
    private lateinit var btnSkeleton: MaterialButton
    private lateinit var btnDownload: MaterialButton
    private lateinit var btnShare: MaterialButton
    private lateinit var btnPlayerBack: ImageButton

    private var page = Page.LIST
    private var cameraProvider: ProcessCameraProvider? = null
    private var videoCapture: VideoCapture<Recorder>? = null
    private var recording: Recording? = null
    private var recordingFile: File? = null
    private var cameraBound = false
    private var pendingImport = false

    private var prepareMeta: ClipMeta? = null
    private var prepareRetriever: MediaMetadataRetriever? = null
    private var prepareFrame: Bitmap? = null
    private var prepareTMs = 0
    private var prepareInMs = 0
    private var prepareOutMs: Int? = null
    private val prepareSeeds = LinkedHashMap<Int, SeedMark>()
    private val birthdayCal: Calendar = Calendar.getInstance().apply {
        set(1990, Calendar.JANUARY, 1)
    }
    private var loadingProfile = false
    private val genderOrder = listOf(
        AthleteGender.UNSPECIFIED,
        AthleteGender.FEMALE,
        AthleteGender.MALE,
        AthleteGender.OTHER,
    )

    private var player: MediaPlayer? = null
    private var pendingPlayerFile: File? = null
    private var timeline: List<PoseFrame> = emptyList()
    private var playing = false
    private var playerEnded = false
    private var playerMeta: ClipMeta? = null
    private var playerReportModel: StageReport? = null
    private var playerFeedback: FrameFeedbackFile = FrameFeedback.empty("")
    private var pendingDownloadFile: File? = null
    private var playStartMs = 0L
    private var playEndMs = Long.MAX_VALUE / 4
    private var playerSpeed = 1f
    private var playerSeekPending = false
    private var startAfterSeek = false
    private var pendingSeekMs = 0L
    private var seekRetries = 0
    private var playerRetriever: MediaMetadataRetriever? = null
    private var pausedFrame: Bitmap? = null
    private var hudTMs = 0L
    private var hudVideoFrame = 0
    private var hudPoseI: Int? = null
    private var curriculumCache: Curriculum? = null
    private val chromeHide = Runnable { hidePlayerChrome() }

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted ->
        if (granted) {
            startCamera()
        } else {
            showCaptureDenied(permission = true)
        }
    }

    private val pickMedia = registerForActivityResult(
        ActivityResultContracts.OpenDocument(),
    ) { uri ->
        if (uri == null) {
            if (pendingImport) {
                pendingImport = false
                showPage(Page.LIST)
            }
            return@registerForActivityResult
        }
        importUri(uri)
    }

    private val createDownload = registerForActivityResult(
        ActivityResultContracts.CreateDocument("image/jpeg"),
    ) { uri ->
        val src = pendingDownloadFile
        pendingDownloadFile = null
        if (uri == null || src == null || !src.isFile) {
            return@registerForActivityResult
        }
        try {
            contentResolver.openOutputStream(uri)?.use { out ->
                src.inputStream().use { input -> input.copyTo(out) }
            } ?: throw IllegalStateException("stream")
            Toast.makeText(this, I18n.t("Download"), Toast.LENGTH_SHORT).show()
        } catch (_: Exception) {
            Toast.makeText(this, I18n.t("Export failed"), Toast.LENGTH_SHORT).show()
        }
    }

    private val overlayTicker = object : Runnable {
        override fun run() {
            val media = player ?: return
            if (playerSeekPending) {
                overlayHandler.postDelayed(this, 33)
                return
            }
            val pos = media.currentPosition.toLong()
            if (ClipRange.pastPlayEnd(pos, playEndMs)) {
                media.pause()
                playing = false
                playerEnded = true
                btnPlay.setIconResource(R.drawable.ic_play)
                btnPlay.setIconOnly(I18n.t("Play"))
                showPlayerChrome(autoHide = false)
                seekClosest(playEndMs - 1L, startWhenDone = false)
                return
            }
            updatePlayerHud(pos)
            overlayHandler.postDelayed(this, 33)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        I18n.init(this)
        library = Library(File(filesDir, "library"))
        athletes = Athletes(File(filesDir, "athletes.json"))
        ingest = Ingest(this, library)
        engine = PoseEngine(this)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        setContentView(R.layout.activity_main)
        applySafeArea(findViewById(R.id.root))
        bindViews()
        bindClicks()
        setupLanguage()
        retranslate()
        reloadList()
        onBackPressedDispatcher.addCallback(
            this,
            object : OnBackPressedCallback(true) {
                override fun handleOnBackPressed() {
                    if (page == Page.LIST) {
                        isEnabled = false
                        onBackPressedDispatcher.onBackPressed()
                        isEnabled = true
                    } else {
                        goList()
                    }
                }
            },
        )
    }

    override fun onDestroy() {
        super.onDestroy()
        overlayHandler.removeCallbacks(overlayTicker)
        recordHandler.removeCallbacksAndMessages(null)
        releasePlayer()
        prepareRetriever?.release()
        cameraExecutor.shutdown()
        recording?.stop()
        cameraProvider?.unbindAll()
    }

    private fun bindViews() {
        pageList = findViewById(R.id.page_list)
        pageCapture = findViewById(R.id.page_capture)
        pagePrepare = findViewById(R.id.page_prepare)
        pagePlayer = findViewById(R.id.page_player)
        loading = findViewById(R.id.loading)
        loadingCaption = findViewById(R.id.loading_caption)
        clipList = findViewById(R.id.clip_list)
        btnCamera = findViewById(R.id.btn_camera)
        btnImport = findViewById(R.id.btn_import)
        labelLanguage = findViewById(R.id.label_language)
        spinnerLanguage = findViewById(R.id.spinner_language)
        capturePreview = findViewById(R.id.capture_preview)
        captureHint = findViewById(R.id.capture_hint)
        captureDenied = findViewById(R.id.capture_denied)
        captureDeniedTitle = findViewById(R.id.capture_denied_title)
        captureDeniedBody = findViewById(R.id.capture_denied_body)
        btnAllowCamera = findViewById(R.id.btn_allow_camera)
        btnRecord = findViewById(R.id.btn_record)
        btnCaptureImport = findViewById(R.id.btn_capture_import)
        btnCaptureBack = findViewById(R.id.btn_capture_back)
        prepareCanvas = findViewById(R.id.prepare_canvas)
        prepareTime = findViewById(R.id.prepare_time)
        prepareTimeline = findViewById(R.id.prepare_timeline)
        prepareRange = findViewById(R.id.prepare_range)
        btnStartAnalysis = findViewById(R.id.btn_start_analysis)
        btnPrepareBack = findViewById(R.id.btn_prepare_back)
        labelProfile = findViewById(R.id.label_profile)
        labelName = findViewById(R.id.label_name)
        labelBirthday = findViewById(R.id.label_birthday)
        labelHeight = findViewById(R.id.label_height)
        labelGender = findViewById(R.id.label_gender)
        labelWeight = findViewById(R.id.label_weight)
        labelSki = findViewById(R.id.label_ski)
        unitHeight = findViewById(R.id.unit_height)
        unitWeight = findViewById(R.id.unit_weight)
        unitSki = findViewById(R.id.unit_ski)
        spinnerProfile = findViewById(R.id.spinner_profile)
        spinnerGender = findViewById(R.id.spinner_gender)
        inputName = findViewById(R.id.input_name)
        inputBirthday = findViewById(R.id.input_birthday)
        inputHeight = findViewById(R.id.input_height)
        inputWeight = findViewById(R.id.input_weight)
        inputSki = findViewById(R.id.input_ski)
        playerStage = findViewById(R.id.player_stage)
        playerVideo = findViewById(R.id.player_video)
        playerImage = findViewById(R.id.player_image)
        playerOverlay = findViewById(R.id.player_overlay)
        playerChrome = findViewById(R.id.player_chrome)
        playerTimeline = findViewById(R.id.player_timeline)
        playerReport = findViewById(R.id.player_report)
        btnPlay = findViewById(R.id.btn_play)
        btnLocator = findViewById(R.id.btn_locator)
        btnSpeed = findViewById(R.id.btn_speed)
        btnLike = findViewById(R.id.btn_like)
        btnUnlike = findViewById(R.id.btn_unlike)
        btnSkeleton = findViewById(R.id.btn_skeleton)
        btnDownload = findViewById(R.id.btn_download)
        btnShare = findViewById(R.id.btn_share)
        btnPlayerBack = findViewById(R.id.btn_player_back)
        capturePreview.implementationMode = PreviewView.ImplementationMode.COMPATIBLE
        capturePreview.scaleType = PreviewView.ScaleType.FILL_CENTER
        playerVideo.surfaceTextureListener = object : TextureView.SurfaceTextureListener {
            override fun onSurfaceTextureAvailable(surface: SurfaceTexture, width: Int, height: Int) {
                pendingPlayerFile?.let { attachPlayer(it) }
            }

            override fun onSurfaceTextureSizeChanged(surface: SurfaceTexture, width: Int, height: Int) = Unit

            override fun onSurfaceTextureDestroyed(surface: SurfaceTexture): Boolean {
                overlayHandler.removeCallbacks(overlayTicker)
                playerSeekPending = false
                startAfterSeek = false
                player?.release()
                player = null
                playing = false
                return true
            }

            override fun onSurfaceTextureUpdated(surface: SurfaceTexture) = Unit
        }
    }

    private fun bindClicks() {
        btnCamera.setOnClickListener { openCapture() }
        btnImport.setOnClickListener { openImport() }
        btnCaptureImport.setOnClickListener { pickMedia.launch(arrayOf("video/*", "image/*")) }
        btnCaptureBack.setOnClickListener { goList() }
        btnAllowCamera.setOnClickListener { requestCameraOrSettings() }
        btnRecord.setOnClickListener { toggleRecord() }
        btnPrepareBack.setOnClickListener { goList() }
        btnStartAnalysis.setOnClickListener { startAnalysisFromPrepare() }
        btnPlayerBack.setOnClickListener { goList() }
        btnPlay.setOnClickListener { togglePlay() }
        btnLocator.setOnClickListener { copyLocator() }
        btnSpeed.setOnClickListener { cycleSpeed() }
        btnLike.setOnClickListener { voteStage("like") }
        btnUnlike.setOnClickListener { voteStage("unlike") }
        btnSkeleton.setOnClickListener { voteSkeleton() }
        btnDownload.setOnClickListener { downloadOverlay() }
        btnShare.setOnClickListener { showShareMenu() }
        playerStage.onTap = { showPlayerChrome(autoHide = playing) }
        playerTimeline.onPlayhead = { tMs -> seekPlayer(tMs.toLong(), pause = false) }
        playerTimeline.setTrimEnabled(false)
        playerReport.onSeek = { tMs -> seekPlayer(tMs.toLong(), pause = true) }
        prepareCanvas.boxCommitted = {
            val box = prepareCanvas.boxNorm()
            if (box != null) {
                prepareSeeds[seedFrameKey(prepareTMs.toDouble())] = SeedMark(prepareTMs.toDouble(), box)
                syncPrepareKeyframes()
            }
        }
        prepareTimeline.onPlayhead = { tMs ->
            prepareTMs = tMs
            showPrepareFrame()
        }
        prepareTimeline.onRange = { startMs, endMs ->
            prepareInMs = startMs
            prepareOutMs = endMs
            refreshPrepareLabels()
        }
        inputBirthday.setOnClickListener { showBirthdayPicker() }
        spinnerProfile.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                if (loadingProfile) {
                    return
                }
                val key = (spinnerProfile.selectedItem as? ProfileOption)?.key.orEmpty()
                if (key.isNotEmpty()) {
                    applyProfileKey(key)
                }
            }

            override fun onNothingSelected(parent: AdapterView<*>?) = Unit
        }
    }

    private fun setupLanguage() {
        val labels = I18n.SUPPORTED.map { I18n.LABELS[it] ?: it }
        val adapter = ArrayAdapter(this, R.layout.spinner_item, labels)
        adapter.setDropDownViewResource(R.layout.spinner_item)
        spinnerLanguage.adapter = adapter
        spinnerLanguage.setSelection(I18n.SUPPORTED.indexOf(I18n.language()).coerceAtLeast(0), false)
        spinnerLanguage.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                val code = I18n.SUPPORTED.getOrNull(position) ?: I18n.DEFAULT
                if (code != I18n.language()) {
                    I18n.setLanguage(code)
                    retranslate()
                    reprojectReports()
                    reloadList()
                }
            }

            override fun onNothingSelected(parent: AdapterView<*>?) = Unit
        }
    }

    private fun retranslate() {
        btnCamera.setIconOnly(I18n.t("Camera"))
        btnImport.setIconOnly(I18n.t("Import"))
        labelLanguage.text = I18n.t("Language")
        captureHint.text = I18n.t("Camera preview")
        btnCaptureImport.setIconOnly(I18n.t("Import…"))
        syncRecordButton()
        btnCaptureBack.contentDescription = I18n.t("Back")
        btnPrepareBack.contentDescription = I18n.t("Back")
        btnPlayerBack.contentDescription = I18n.t("Back")
        btnStartAnalysis.setIconOnly(I18n.t("Start analysis"))
        labelProfile.text = I18n.t("Saved profile")
        labelName.text = I18n.t("Name")
        labelBirthday.text = I18n.t("Birthday")
        labelHeight.text = I18n.t("Height")
        labelGender.text = I18n.t("Gender")
        labelWeight.text = I18n.t("Weight")
        labelSki.text = I18n.t("Ski length")
        unitHeight.text = I18n.t(" cm")
        unitWeight.text = I18n.t(" kg")
        unitSki.text = I18n.t(" cm")
        rebuildGenderSpinner()
        reloadProfiles(currentProfileKey())
        refreshBirthdayLabel()
        btnPlay.setIconOnly(if (playing) I18n.t("Pause") else I18n.t("Play"))
        btnSpeed.contentDescription = I18n.t("Speed")
        btnLike.setIconOnly(I18n.t("Like"))
        btnUnlike.setIconOnly(I18n.t("Unlike"))
        btnSkeleton.setIconOnly(I18n.t("Bad skeleton"))
        btnDownload.setIconOnly(I18n.t("Download"))
        btnShare.setIconOnly(I18n.t("Share"))
        playerReport.retranslate()
        refreshPrepareLabels()
    }

    private fun reloadList() {
        clipList.removeAllViews()
        val inflater = LayoutInflater.from(this)
        for (meta in library.listClips()) {
            val row = inflater.inflate(R.layout.item_clip, clipList, false)
            val thumb = row.findViewById<ImageView>(R.id.thumb)
            val name = row.findViewById<TextView>(R.id.clip_name)
            val duration = row.findViewById<TextView>(R.id.clip_duration)
            val status = row.findViewById<TextView>(R.id.clip_status)
            val spinner = row.findViewById<View>(R.id.clip_spinner)
            val report = row.findViewById<MaterialButton>(R.id.btn_report)
            val reanalyze = row.findViewById<MaterialButton>(R.id.btn_reanalyze)
            val delete = row.findViewById<MaterialButton>(R.id.btn_delete)
            val thumbFile = library.thumbFile(meta.clipId)
            if (thumbFile.isFile) {
                thumb.setImageBitmap(BitmapFactory.decodeFile(thumbFile.absolutePath))
            } else {
                thumb.setImageDrawable(null)
            }
            name.text = meta.displayName
            duration.text = Library.formatDurationMs(meta.durationMs, meta.kind == ClipKind.IMAGE)
            var statusText = I18n.t(Library.statusKey(meta.status))
            if (meta.error != null) {
                statusText = I18n.t("{status} (failed, retry)", mapOf("status" to statusText))
            }
            status.text = statusText
            status.setTextColor(
                ContextCompat.getColor(
                    this,
                    if (meta.status == ClipStatus.PENDING) R.color.chip_pending else R.color.chip_done,
                ),
            )
            spinner.visibility = if (meta.status == ClipStatus.PROCESSING) View.VISIBLE else View.GONE
            val hasReport = meta.status == ClipStatus.DONE && library.stageReportFile(meta.clipId).isFile
            report.visibility = if (hasReport) View.VISIBLE else View.GONE
            report.contentDescription = I18n.t("Report")
            reanalyze.contentDescription = I18n.t("Reanalyze")
            delete.contentDescription = I18n.t("Delete")
            report.text = null
            reanalyze.text = null
            delete.text = null
            reanalyze.visibility = if (meta.status == ClipStatus.PROCESSING) View.GONE else View.VISIBLE
            row.setOnClickListener { onRowClick(meta.clipId) }
            report.setOnClickListener { openPlayer(meta.clipId) }
            reanalyze.setOnClickListener {
                library.prepareReanalyze(meta.clipId)
                openPrepare(meta.clipId)
            }
            delete.setOnClickListener { confirmDelete(meta.clipId) }
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT,
            )
            params.bottomMargin = dp(ReportTheme.SPACE_PANEL)
            clipList.addView(row, params)
        }
    }

    private fun onRowClick(clipId: String) {
        val meta = library.listClips().firstOrNull { it.clipId == clipId } ?: return
        when (meta.status) {
            ClipStatus.PENDING -> openPrepare(clipId)
            ClipStatus.PROCESSING -> AlertDialog.Builder(this)
                .setTitle(I18n.t("Processing"))
                .setMessage(I18n.t("This clip is still processing. Play it when it is done."))
                .setPositiveButton(I18n.t("OK"), null)
                .show()
            ClipStatus.DONE -> openPlayer(clipId)
        }
    }

    private fun confirmDelete(clipId: String) {
        AlertDialog.Builder(this)
            .setTitle(I18n.t("Delete"))
            .setMessage(I18n.t("Delete this clip and its local files? This cannot be undone."))
            .setPositiveButton(I18n.t("OK")) { _, _ ->
                library.deleteClip(clipId)
                if (page != Page.LIST) {
                    goList()
                } else {
                    reloadList()
                }
            }
            .setNegativeButton(I18n.t("Cancel"), null)
            .show()
    }

    private fun openCapture() {
        pendingImport = false
        showPage(Page.CAPTURE)
        captureDenied.visibility = View.GONE
        if (hasCameraPermission()) {
            startCamera()
        } else {
            permissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    private fun openImport() {
        pendingImport = true
        showPage(Page.CAPTURE)
        stopCamera()
        capturePreview.visibility = View.GONE
        captureHint.visibility = View.GONE
        findViewById<View>(R.id.capture_bar).visibility = View.GONE
        btnCaptureBack.visibility = View.GONE
        pickMedia.launch(arrayOf("video/*", "image/*"))
    }

    private fun goList() {
        pendingImport = false
        stopCamera()
        releasePrepare()
        releasePlayer()
        findViewById<View>(R.id.capture_bar).visibility = View.VISIBLE
        btnCaptureBack.visibility = View.VISIBLE
        capturePreview.visibility = View.VISIBLE
        captureHint.visibility = View.VISIBLE
        showPage(Page.LIST)
        reloadList()
    }

    private fun importUri(uri: Uri) {
        showLoading("import")
        cameraExecutor.execute {
            try {
                ingest.fromUri(uri)
                runOnUiThread {
                    hideLoadingIfIdle()
                    goList()
                }
            } catch (exc: Exception) {
                Log.e(TAG, "import failed", exc)
                runOnUiThread {
                    hideLoadingIfIdle()
                    AlertDialog.Builder(this)
                        .setTitle(I18n.t("Import failed"))
                        .setMessage(I18n.t("Could not read video."))
                        .setPositiveButton(I18n.t("OK"), null)
                        .show()
                    goList()
                }
            }
        }
    }

    private fun startCamera() {
        captureDenied.visibility = View.GONE
        capturePreview.visibility = View.VISIBLE
        if (cameraBound) {
            return
        }
        val future = ProcessCameraProvider.getInstance(this)
        future.addListener({
            try {
                val provider = future.get()
                cameraProvider = provider
                val preview = Preview.Builder().build().also {
                    it.setSurfaceProvider(capturePreview.surfaceProvider)
                }
                val recorder = Recorder.Builder()
                    .setQualitySelector(
                        QualitySelector.fromOrderedList(
                            listOf(Quality.HD, Quality.SD),
                            FallbackStrategy.lowerQualityOrHigherThan(Quality.SD),
                        ),
                    )
                    .build()
                val capture = VideoCapture.withOutput(recorder)
                videoCapture = capture
                val selectors = listOf(
                    CameraSelector.DEFAULT_BACK_CAMERA,
                    CameraSelector.DEFAULT_FRONT_CAMERA,
                    CameraSelector.Builder().build(),
                )
                var bound = false
                var lastError: Exception? = null
                for (selector in selectors) {
                    try {
                        provider.unbindAll()
                        provider.bindToLifecycle(this, selector, preview, capture)
                        bound = true
                        cameraBound = true
                        break
                    } catch (exc: Exception) {
                        lastError = exc
                    }
                }
                if (!bound) {
                    cameraBound = false
                    Log.e(TAG, "bindCamera failed", lastError)
                    showCaptureDenied(permission = false)
                }
            } catch (exc: Exception) {
                cameraBound = false
                Log.e(TAG, "Camera provider failed", exc)
                showCaptureDenied(permission = false)
            }
        }, ContextCompat.getMainExecutor(this))
    }

    private fun stopCamera() {
        recordHandler.removeCallbacksAndMessages(null)
        if (recording != null) {
            recording?.stop()
            recording = null
        }
        cameraProvider?.unbindAll()
        cameraBound = false
        videoCapture = null
        syncRecordButton()
    }

    private fun toggleRecord() {
        if (recording != null) {
            recording?.stop()
            return
        }
        val capture = videoCapture
        if (capture == null) {
            AlertDialog.Builder(this)
                .setTitle(I18n.t("Camera device"))
                .setMessage(I18n.t("Could not open the camera."))
                .setPositiveButton(I18n.t("OK"), null)
                .show()
            return
        }
        val file = File(cacheDir, "record_${System.currentTimeMillis()}.mp4")
        recordingFile = file
        val opts = FileOutputOptions.Builder(file).build()
        recording = capture.output
            .prepareRecording(this, opts)
            .start(ContextCompat.getMainExecutor(this)) { event ->
                if (event is VideoRecordEvent.Start) {
                    syncRecordButton()
                    recordHandler.postDelayed({ recording?.stop() }, Library.MAX_MS)
                }
                if (event is VideoRecordEvent.Finalize) {
                    recording = null
                    syncRecordButton()
                    recordHandler.removeCallbacksAndMessages(null)
                    if (event.hasError() || !file.isFile || file.length() < 64) {
                        file.delete()
                        if (event.hasError()) {
                            Log.e(TAG, "record error ${event.error}")
                        }
                        return@start
                    }
                    showLoading("import")
                    cameraExecutor.execute {
                        try {
                            ingest.fromFile(file, image = false)
                            file.delete()
                            runOnUiThread {
                                hideLoadingIfIdle()
                                goList()
                            }
                        } catch (exc: Exception) {
                            Log.e(TAG, "ingest record failed", exc)
                            file.delete()
                            runOnUiThread {
                                hideLoadingIfIdle()
                                AlertDialog.Builder(this)
                                    .setTitle(I18n.t("Import failed"))
                                    .setMessage(I18n.t("Could not read video."))
                                    .setPositiveButton(I18n.t("OK"), null)
                                    .show()
                            }
                        }
                    }
                }
            }
        syncRecordButton()
    }

    private fun syncRecordButton() {
        if (recording != null) {
            btnRecord.setIconResource(R.drawable.ic_stop)
            btnRecord.setIconOnly(I18n.t("Stop"))
        } else {
            btnRecord.setIconResource(R.drawable.ic_record)
            btnRecord.setIconOnly(I18n.t("Record"))
        }
    }

    private fun openPrepare(clipId: String) {
        releasePrepare()
        val meta = library.loadMeta(clipId)
        prepareMeta = meta
        prepareInMs = meta.playStartMs
        prepareOutMs = meta.playEndMs
        prepareTMs = prepareInMs
        prepareSeeds.clear()
        val loaded = meta.seeds.ifEmpty {
            meta.seedBox?.let { listOf(SeedMark(0.0, it)) } ?: emptyList()
        }
        for (item in loaded) {
            prepareSeeds[seedFrameKey(item.tMs)] = item
        }
        reloadProfiles(meta.athleteKey)
        when {
            !meta.athleteKey.isNullOrBlank() && athletes.getByKey(meta.athleteKey) != null -> {
                applyProfileKey(meta.athleteKey)
            }
            meta.athlete != null -> fillFromProfile(meta.athlete)
        }
        val media = library.mediaFile(meta)
        if (meta.kind == ClipKind.IMAGE) {
            prepareTimeline.visibility = View.GONE
            val bmp = BitmapFactory.decodeFile(media.absolutePath)
            prepareFrame = bmp
            prepareCanvas.setFrame(bmp)
            prepareCanvas.post { prepareCanvas.setBoxNorm(seedNear(prepareTMs.toDouble())?.box) }
        } else {
            prepareTimeline.visibility = View.VISIBLE
            val retriever = MediaMetadataRetriever()
            retriever.setDataSource(media.absolutePath)
            prepareRetriever = retriever
            val (start, end) = Library.playWindowMs(meta)
            if (meta.playEndMs != null) {
                prepareOutMs = end.toInt()
            }
            if (meta.playStartMs != 0 || meta.playEndMs != null) {
                prepareInMs = start.toInt()
            }
            prepareTMs = prepareInMs
            prepareTimeline.bindVideo(media.absolutePath, meta.durationMs.coerceAtLeast(1))
            prepareTimeline.setRange(prepareInMs, prepareOutMs)
            syncPrepareKeyframes()
            showPrepareFrame()
        }
        showPage(Page.PREPARE)
        refreshPrepareLabels()
    }

    private fun showPrepareFrame() {
        val retriever = prepareRetriever ?: return
        val bmp = retriever.getFrameAtTime(prepareTMs * 1000L, MediaMetadataRetriever.OPTION_CLOSEST)
        val old = prepareFrame
        prepareFrame = bmp
        prepareCanvas.setFrame(bmp)
        if (old != null && old != bmp && !old.isRecycled) {
            old.recycle()
        }
        prepareCanvas.post { prepareCanvas.setBoxNorm(seedNear(prepareTMs.toDouble())?.box) }
        prepareTimeline.setPlayheadMs(prepareTMs)
        refreshPrepareLabels()
    }

    private fun refreshPrepareLabels() {
        val meta = prepareMeta ?: return
        val total = meta.durationMs
        prepareTime.text = "${Library.formatDurationMs(prepareTMs)} / ${Library.formatDurationMs(total)}"
        val out = prepareOutMs ?: total
        prepareRange.text = I18n.t(
            "In {lo:.1f}s → out {hi:.1f}s (logical, original file unchanged)",
            mapOf(
                "lo" to String.format(Locale.US, "%.1f", prepareInMs / 1000.0),
                "hi" to String.format(Locale.US, "%.1f", out / 1000.0),
            ),
        )
    }

    private fun startAnalysisFromPrepare() {
        val meta = prepareMeta ?: return
        if (prepareSeeds.isEmpty()) {
            val live = prepareCanvas.boxNorm()
            if (live != null) {
                prepareSeeds[seedFrameKey(prepareTMs.toDouble())] = SeedMark(prepareTMs.toDouble(), live)
            }
        }
        if (prepareSeeds.isEmpty()) {
            AlertDialog.Builder(this)
                .setTitle(I18n.t("No box"))
                .setMessage(I18n.t("Record at least one person box."))
                .setPositiveButton(I18n.t("OK"), null)
                .show()
            return
        }
        val athlete = readAthlete()
        if (athlete == null) {
            AlertDialog.Builder(this)
                .setTitle(I18n.t("Athlete info required"))
                .setMessage(I18n.t("Enter name, height, weight, and ski length, or pick a saved profile."))
                .setPositiveButton(I18n.t("OK"), null)
                .show()
            return
        }
        reloadProfiles(athlete.key)
        val seeds = prepareSeeds.values.sortedBy { it.tMs }
        val next = meta.copy(
            seeds = seeds,
            seedBox = seeds.first().box,
            playStartMs = prepareInMs,
            playEndMs = prepareOutMs,
            athleteKey = athlete.key,
            athlete = athlete,
            status = ClipStatus.PROCESSING,
            error = null,
        )
        library.saveMeta(next)
        enqueueAnalysis(next.clipId)
        goList()
    }

    private fun enqueueAnalysis(clipId: String) {
        analyzing.set(true)
        showLoading("analyze")
        cameraExecutor.execute {
            try {
                val meta = library.loadMeta(clipId)
                val markers = engine.createPair()
                val frames = try {
                    if (meta.kind == ClipKind.IMAGE) {
                        val bmp = BitmapFactory.decodeFile(library.mediaFile(meta).absolutePath)
                            ?: throw IllegalStateException("Could not read video.")
                        VideoPose.analyzeBitmap(
                            bmp,
                            markers,
                            engine.device.get(),
                            meta.seeds,
                            meta.seedBox,
                        )
                    } else {
                        val retriever = MediaMetadataRetriever()
                        try {
                            retriever.setDataSource(library.mediaFile(meta).absolutePath)
                            val (start, end) = Library.playWindowMs(meta)
                            val fps = if (meta.fps > 1.0) meta.fps else 30.0
                            VideoPose.analyze(
                                retriever,
                                markers,
                                engine.device.get(),
                                start,
                                end,
                                meta.seeds,
                                meta.seedBox,
                                fps,
                            ) { _, _ -> }
                        } finally {
                            retriever.release()
                        }
                    }
                } finally {
                    markers.close()
                }
                AnalysisJson.save(library.analysisFile(clipId), clipId, frames)
                val fps = if (meta.fps > 1.0) meta.fps else 15.0
                writeStageReport(clipId, frames, fps)
                library.saveMeta(meta.copy(status = ClipStatus.DONE, error = null))
            } catch (exc: Exception) {
                Log.e(TAG, "analyze failed", exc)
                try {
                    val meta = library.loadMeta(clipId)
                    library.saveMeta(meta.copy(status = ClipStatus.PROCESSING, error = exc.message))
                } catch (_: Exception) {
                }
            } finally {
                analyzing.set(false)
                runOnUiThread {
                    hideLoadingIfIdle()
                    if (page == Page.LIST) {
                        reloadList()
                    }
                }
            }
        }
    }

    private fun openPlayer(clipId: String) {
        releasePlayer()
        val meta = library.loadMeta(clipId)
        playerMeta = meta
        timeline = AnalysisJson.load(library.analysisFile(clipId))
        playerReportModel = StageReportJson.load(library.stageReportFile(clipId))
        playerFeedback = FrameFeedback.load(library.frameFeedbackFile(clipId), clipId)
        val (start, end) = Library.playWindowMs(meta)
        playStartMs = start
        playEndMs = if (meta.durationMs > 0) {
            end.coerceAtMost(meta.durationMs.toLong())
        } else {
            end
        }
        playerSpeed = 1f
        playerEnded = false
        val media = library.mediaFile(meta)
        playerStage.setAspect(meta.width, meta.height)
        playerReport.bind(playerReportModel)
        showPage(Page.PLAYER)
        val video = meta.kind == ClipKind.VIDEO
        playerVideo.visibility = if (video) View.VISIBLE else View.GONE
        playerImage.visibility = if (video) View.GONE else View.VISIBLE
        btnPlay.visibility = if (video) View.VISIBLE else View.GONE
        btnSpeed.visibility = if (video) View.VISIBLE else View.GONE
        playerTimeline.visibility = if (video) View.VISIBLE else View.GONE
        if (video) {
            playerTimeline.bindVideo(media.absolutePath, meta.durationMs.coerceAtLeast(1))
            playerTimeline.setTrimEnabled(false)
            playerTimeline.setRange(start.toInt(), meta.playEndMs)
            playerTimeline.setKeyframes(timeline.map { it.tMs.toInt() })
            bindPlayerRetriever(media)
            pendingPlayerFile = media
            if (playerVideo.isAvailable) {
                attachPlayer(media)
            }
        } else {
            playerTimeline.clear()
            val bmp = BitmapFactory.decodeFile(media.absolutePath)
            playerImage.setImageBitmap(bmp)
            updatePlayerHud(0L)
            showPlayerChrome(autoHide = false)
        }
        syncLocatorLabel()
        syncFeedbackButtons()
        btnSpeed.text = "1×"
        retranslate()
    }

    private fun attachPlayer(file: File) {
        val texture = playerVideo.surfaceTexture ?: return
        player?.release()
        player = null
        playerSeekPending = false
        startAfterSeek = false
        val media = MediaPlayer()
        player = media
        media.setDataSource(file.absolutePath)
        media.setSurface(Surface(texture))
        media.setVideoScalingMode(MediaPlayer.VIDEO_SCALING_MODE_SCALE_TO_FIT)
        media.isLooping = false
        media.setOnSeekCompleteListener { onPlayerSeekComplete(it) }
        media.setOnPreparedListener {
            val vw = it.videoWidth
            val vh = it.videoHeight
            if (vw > 0 && vh > 0) {
                playerStage.setAspect(vw, vh)
            }
            applySpeed()
            playerEnded = false
            seekClosest(playStartMs, startWhenDone = true)
            showPlayerChrome(autoHide = true)
        }
        media.setOnCompletionListener {
            playing = false
            playerEnded = true
            btnPlay.setIconResource(R.drawable.ic_play)
            btnPlay.setIconOnly(I18n.t("Play"))
            showPlayerChrome(autoHide = false)
        }
        media.setOnErrorListener { _, what, extra ->
            Log.e(TAG, "MediaPlayer error $what $extra")
            true
        }
        media.prepareAsync()
    }

    private fun bindPlayerRetriever(file: File) {
        playerRetriever?.release()
        playerRetriever = null
        val next = MediaMetadataRetriever()
        try {
            next.setDataSource(file.absolutePath)
            playerRetriever = next
        } catch (_: Exception) {
            next.release()
        }
    }

    private fun showPausedVideoFrame(tMs: Long) {
        val retriever = playerRetriever ?: return
        val clamped = ClipRange.clampPlayheadMs(tMs, playStartMs, playEndMs)
        val bmp = retriever.getFrameAtTime(
            clamped * 1000L,
            MediaMetadataRetriever.OPTION_CLOSEST,
        ) ?: return
        val old = pausedFrame
        pausedFrame = bmp
        playerImage.setImageBitmap(bmp)
        playerImage.visibility = View.VISIBLE
        if (old != null && old != bmp && !old.isRecycled) {
            old.recycle()
        }
    }

    private fun hidePausedVideoFrame() {
        playerImage.visibility = View.GONE
        playerImage.setImageBitmap(null)
        val old = pausedFrame
        pausedFrame = null
        if (old != null && !old.isRecycled) {
            old.recycle()
        }
    }

    private fun seekClosest(tMs: Long, startWhenDone: Boolean) {
        val media = player ?: return
        val clamped = ClipRange.clampPlayheadMs(tMs, playStartMs, playEndMs)
        pendingSeekMs = clamped
        playerSeekPending = true
        startAfterSeek = startWhenDone
        seekRetries = 0
        media.seekTo(clamped, MediaPlayer.SEEK_CLOSEST)
    }

    private fun onPlayerSeekComplete(media: MediaPlayer) {
        val reported = media.currentPosition.toLong()
        if (startAfterSeek && reported < playStartMs && seekRetries < 2) {
            seekRetries += 1
            media.seekTo(pendingSeekMs, MediaPlayer.SEEK_CLOSEST)
            return
        }
        seekRetries = 0
        playerSeekPending = false
        if (startAfterSeek) {
            startAfterSeek = false
            playerEnded = false
            hidePausedVideoFrame()
            media.start()
            applySpeed()
            playing = true
            btnPlay.setIconResource(R.drawable.ic_pause)
            btnPlay.setIconOnly(I18n.t("Pause"))
            overlayHandler.removeCallbacks(overlayTicker)
            overlayHandler.post(overlayTicker)
            showPlayerChrome(autoHide = true)
        } else if (!playing) {
            showPausedVideoFrame(pendingSeekMs)
        }
        updatePlayerHud(pendingSeekMs)
    }

    private fun togglePlay() {
        val media = player ?: return
        if (media.isPlaying) {
            media.pause()
            playing = false
            overlayHandler.removeCallbacks(overlayTicker)
            btnPlay.setIconResource(R.drawable.ic_play)
            btnPlay.setIconOnly(I18n.t("Play"))
            showPausedVideoFrame(media.currentPosition.toLong())
            showPlayerChrome(autoHide = false)
            return
        }
        val pos = media.currentPosition.toLong()
        if (playerEnded || ClipRange.pastPlayEnd(pos, playEndMs) || pos < playStartMs) {
            seekClosest(playStartMs, startWhenDone = true)
            return
        }
        hidePausedVideoFrame()
        media.start()
        playing = true
        overlayHandler.post(overlayTicker)
        btnPlay.setIconResource(R.drawable.ic_pause)
        btnPlay.setIconOnly(I18n.t("Pause"))
        showPlayerChrome(autoHide = true)
    }

    private fun seekPlayer(tMs: Long, pause: Boolean) {
        val clamped = ClipRange.clampPlayheadMs(tMs, playStartMs, playEndMs)
        if (pause && playing) {
            player?.pause()
            playing = false
            overlayHandler.removeCallbacks(overlayTicker)
            btnPlay.setIconResource(R.drawable.ic_play)
            btnPlay.setIconOnly(I18n.t("Play"))
            showPlayerChrome(autoHide = false)
        }
        playerEnded = false
        playerTimeline.setPlayheadMs(clamped.toInt())
        if (!playing) {
            showPausedVideoFrame(clamped)
            updatePlayerHud(clamped)
        }
        seekClosest(clamped, startWhenDone = false)
        showPlayerChrome(autoHide = playing)
    }

    private fun updatePlayerHud(tMs: Long) {
        hudTMs = tMs.coerceAtLeast(0L)
        val fps = playerMeta?.fps?.takeIf { it > 1.0 } ?: 30.0
        hudVideoFrame = (hudTMs / 1000.0 * fps).toInt()
        val frame = PoseTimeline.nearest(timeline, hudTMs)
        hudPoseI = if (frame == null) null else timeline.indexOf(frame).takeIf { it >= 0 }
        if (frame != null) {
            playerOverlay.setPoses(frame.poses, frame.width, frame.height, frame.bbox)
        } else {
            playerOverlay.setPoses(emptyList(), 1, 1, null)
        }
        playerTimeline.setPlayheadMs(hudTMs.toInt())
        syncLocatorLabel()
        syncFeedbackButtons()
    }

    private fun showPlayerChrome(autoHide: Boolean) {
        playerChrome.visibility = View.VISIBLE
        overlayHandler.removeCallbacks(chromeHide)
        if (autoHide && playing) {
            overlayHandler.postDelayed(chromeHide, 3000)
        }
    }

    private fun hidePlayerChrome() {
        if (playing && !playerEnded) {
            playerChrome.visibility = View.GONE
        }
    }

    private fun cycleSpeed() {
        val idx = SPEEDS.indexOfFirst { kotlin.math.abs(it - playerSpeed) < 0.01f }
        playerSpeed = SPEEDS[(idx + 1) % SPEEDS.size]
        btnSpeed.text = "${trimSpeed(playerSpeed)}×"
        applySpeed()
        showPlayerChrome(autoHide = playing)
    }

    private fun applySpeed() {
        val media = player ?: return
        try {
            media.playbackParams = PlaybackParams().setSpeed(playerSpeed)
        } catch (exc: Exception) {
            Log.e(TAG, "speed failed", exc)
        }
    }

    private fun curriculum(): Curriculum {
        val cached = curriculumCache
        if (cached != null) {
            return cached
        }
        val loaded = CurriculumLoader.loadFromAssets(this)
        curriculumCache = loaded
        return loaded
    }

    private fun writeStageReport(clipId: String, frames: List<PoseFrame>, fps: Double) {
        val report = Assess.assessClip(
            clipId,
            AnalysisJson.toAssessFrames(frames),
            fps,
            curriculum(),
            I18n.language(),
        )
        StageReportJson.save(library.stageReportFile(clipId), report)
    }

    private fun reprojectReports() {
        cameraExecutor.execute {
            try {
                val cur = curriculum()
                val lang = I18n.language()
                for (meta in library.listClips()) {
                    if (meta.status != ClipStatus.DONE) {
                        continue
                    }
                    val frames = AnalysisJson.load(library.analysisFile(meta.clipId))
                    if (frames.none { it.blaze33.size >= 33 }) {
                        continue
                    }
                    val fps = if (meta.fps > 1.0) meta.fps else 15.0
                    val report = Assess.assessClip(
                        meta.clipId,
                        AnalysisJson.toAssessFrames(frames),
                        fps,
                        cur,
                        lang,
                    )
                    StageReportJson.save(library.stageReportFile(meta.clipId), report)
                }
            } catch (exc: Exception) {
                Log.e(TAG, "reproject failed", exc)
            }
            runOnUiThread {
                playerReportModel = playerMeta?.let { StageReportJson.load(library.stageReportFile(it.clipId)) }
                playerReport.bind(playerReportModel)
                if (page == Page.LIST) {
                    reloadList()
                }
            }
        }
    }

    private fun syncLocatorLabel() {
        val id = playerMeta?.clipId.orEmpty().replace("-", "")
        btnLocator.text = if (id.length >= 8) id.take(8) else id
    }

    private fun syncFeedbackButtons() {
        val entry = playerFeedback.frames[hudVideoFrame.toString()]
        btnLike.isChecked = entry?.stageVote == "like"
        btnUnlike.isChecked = entry?.stageVote == "unlike"
        btnSkeleton.isChecked = entry?.skeletonOk == false
    }

    private fun currentPoseIndex(): Int? = hudPoseI

    private fun voteStage(vote: String) {
        val meta = playerMeta ?: return
        playerFeedback = FrameFeedback.toggleVote(
            library.frameFeedbackFile(meta.clipId),
            meta.clipId,
            hudVideoFrame,
            vote,
            hudTMs.toDouble(),
            currentPoseIndex(),
            playerReportModel?.stageId.orEmpty(),
        )
        syncFeedbackButtons()
        showPlayerChrome(autoHide = playing)
    }

    private fun voteSkeleton() {
        val meta = playerMeta ?: return
        playerFeedback = FrameFeedback.toggleSkeleton(
            library.frameFeedbackFile(meta.clipId),
            meta.clipId,
            hudVideoFrame,
            hudTMs.toDouble(),
            currentPoseIndex(),
            playerReportModel?.stageId.orEmpty(),
        )
        syncFeedbackButtons()
        showPlayerChrome(autoHide = playing)
    }

    private fun copyLocator() {
        val meta = playerMeta ?: return
        val frame = PoseTimeline.nearest(timeline, hudTMs)
        val payload = JSONObject()
            .put("clip_id", meta.clipId)
            .put("short_id", btnLocator.text.toString())
            .put("display_name", meta.displayName)
            .put("video_frame", hudVideoFrame)
            .put("t_ms", hudTMs.toDouble())
            .put("fps", meta.fps)
        val poseI = currentPoseIndex()
        if (poseI == null) {
            payload.put("pose_index", JSONObject.NULL)
        } else {
            payload.put("pose_index", poseI)
        }
        payload.put("stage_id", playerReportModel?.stageId.orEmpty())
        if (frame != null) {
            val blaze = org.json.JSONArray()
            for (joint in frame.blaze33) {
                blaze.put(
                    JSONObject()
                        .put("x", joint.x.toDouble())
                        .put("y", joint.y.toDouble())
                        .put("z", joint.z.toDouble())
                        .put("confidence", joint.confidence.toDouble()),
                )
            }
            payload.put("blaze33", blaze)
        }
        val clipboard = getSystemService(CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText("locator", payload.toString(2)))
        Toast.makeText(this, I18n.t("Frame locator JSON copied"), Toast.LENGTH_SHORT).show()
        showPlayerChrome(autoHide = playing)
    }

    private fun downloadOverlay() {
        val stamped = stampedStill()
        if (stamped == null) {
            Toast.makeText(this, I18n.t("Export failed"), Toast.LENGTH_SHORT).show()
            return
        }
        pendingDownloadFile = stamped
        createDownload.launch(PlayerExport.downloadFileName(playerMeta?.displayName, playerMeta?.clipId))
        showPlayerChrome(autoHide = playing)
    }

    private fun showShareMenu() {
        val menu = PopupMenu(this, btnShare)
        PlayerExport.SHARE_TARGETS.forEachIndexed { i, (key, _) ->
            menu.menu.add(0, i, i, I18n.t(key))
        }
        menu.setOnMenuItemClickListener { item ->
            val target = PlayerExport.SHARE_TARGETS.getOrNull(item.itemId)
                ?: return@setOnMenuItemClickListener false
            val stamped = stampedStill()
            if (stamped == null) {
                Toast.makeText(this, I18n.t("Export failed"), Toast.LENGTH_SHORT).show()
                return@setOnMenuItemClickListener true
            }
            val url = PlayerExport.shareUrl(target.second, I18n.t("Visual Pose"))
            shareFiles(listOf(stamped), imageOnly = true, extraText = url)
            true
        }
        menu.show()
        showPlayerChrome(autoHide = playing)
    }

    private fun stampedStill(): File? {
        val meta = playerMeta ?: return null
        val src = if (meta.kind == ClipKind.IMAGE) {
            BitmapFactory.decodeFile(library.mediaFile(meta).absolutePath)
        } else {
            playerVideo.bitmap ?: run {
                val retriever = MediaMetadataRetriever()
                try {
                    retriever.setDataSource(library.mediaFile(meta).absolutePath)
                    retriever.getFrameAtTime(hudTMs * 1000, MediaMetadataRetriever.OPTION_CLOSEST)
                } finally {
                    retriever.release()
                }
            }
        } ?: return null
        val frame = PoseTimeline.nearest(timeline, hudTMs)
        val out = OverlayStamp.stamp(src, frame)
        if (src !== out && src !== playerVideo.bitmap) {
            src.recycle()
        }
        val dir = File(cacheDir, "share")
        dir.mkdirs()
        val file = File(dir, "overlay.jpg")
        file.outputStream().use { stream ->
            out.compress(Bitmap.CompressFormat.JPEG, 92, stream)
        }
        if (out !== src) {
            out.recycle()
        }
        return file
    }

    private fun shareFiles(files: List<File>, imageOnly: Boolean, extraText: String? = null) {
        if (files.isEmpty()) {
            return
        }
        val uris = ArrayList<Uri>()
        for (file in files) {
            if (!file.isFile) {
                continue
            }
            uris.add(FileProvider.getUriForFile(this, "$packageName.files", file))
        }
        if (uris.isEmpty()) {
            return
        }
        val intent = if (uris.size == 1) {
            Intent(Intent.ACTION_SEND).apply {
                type = if (imageOnly || files.first().name.endsWith(".jpg")) "image/jpeg" else "*/*"
                putExtra(Intent.EXTRA_STREAM, uris[0])
            }
        } else {
            Intent(Intent.ACTION_SEND_MULTIPLE).apply {
                type = "*/*"
                putParcelableArrayListExtra(Intent.EXTRA_STREAM, uris)
            }
        }
        if (!extraText.isNullOrBlank()) {
            intent.putExtra(Intent.EXTRA_TEXT, extraText)
        }
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        val clip = ClipData.newUri(contentResolver, I18n.t("Share"), uris[0])
        for (i in 1 until uris.size) {
            clip.addItem(ClipData.Item(uris[i]))
        }
        intent.clipData = clip
        try {
            startActivity(Intent.createChooser(intent, I18n.t("Share")))
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(this, I18n.t("Export failed"), Toast.LENGTH_SHORT).show()
        }
    }

    private fun releasePlayer() {
        overlayHandler.removeCallbacks(overlayTicker)
        overlayHandler.removeCallbacks(chromeHide)
        player?.release()
        player = null
        playing = false
        playerEnded = false
        playerSeekPending = false
        startAfterSeek = false
        hidePausedVideoFrame()
        playerRetriever?.release()
        playerRetriever = null
        pendingPlayerFile = null
        playerMeta = null
        playerReportModel = null
        playerFeedback = FrameFeedback.empty("")
        playerOverlay.setPoses(emptyList(), 1, 1, null)
        playerTimeline.clear()
    }

    private fun trimSpeed(speed: Float): String {
        return if (speed == speed.toInt().toFloat()) speed.toInt().toString() else speed.toString()
    }

    private fun releasePrepare() {
        prepareTimeline.clear()
        prepareRetriever?.release()
        prepareRetriever = null
        prepareCanvas.setFrame(null)
        prepareFrame?.recycle()
        prepareFrame = null
        prepareMeta = null
        prepareSeeds.clear()
    }

    private fun showPage(next: Page) {
        page = next
        pageList.visibility = if (next == Page.LIST) View.VISIBLE else View.GONE
        pageCapture.visibility = if (next == Page.CAPTURE) View.VISIBLE else View.GONE
        pagePrepare.visibility = if (next == Page.PREPARE) View.VISIBLE else View.GONE
        pagePlayer.visibility = if (next == Page.PLAYER) View.VISIBLE else View.GONE
    }

    private fun showLoading(kind: String) {
        loadingCaption.text = if (kind == "import") {
            I18n.t("Uploading and loading…")
        } else {
            I18n.t("Analyzing pose…")
        }
        loading.visibility = View.VISIBLE
        loading.bringToFront()
    }

    private fun hideLoadingIfIdle() {
        if (!analyzing.get() && recording == null) {
            loading.visibility = View.GONE
        }
    }

    private fun showCaptureDenied(permission: Boolean) {
        captureDenied.visibility = View.VISIBLE
        if (permission) {
            captureDeniedTitle.text = I18n.t("Camera permission required")
            captureDeniedBody.text = I18n.t("Grant camera access to run pose tracking.")
            btnAllowCamera.text = I18n.t("Allow camera")
        } else {
            captureDeniedTitle.text = I18n.t("Camera unavailable")
            captureDeniedBody.text = I18n.t("No camera found. On the emulator, use a virtual scene or webcam.")
            btnAllowCamera.text = I18n.t("Retry")
        }
    }

    private fun hasCameraPermission(): Boolean {
        return ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) ==
            PackageManager.PERMISSION_GRANTED
    }

    private fun requestCameraOrSettings() {
        if (hasCameraPermission()) {
            startCamera()
            return
        }
        if (shouldShowRequestPermissionRationale(Manifest.permission.CAMERA)) {
            permissionLauncher.launch(Manifest.permission.CAMERA)
            return
        }
        startActivity(
            Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                data = Uri.fromParts("package", packageName, null)
            },
        )
    }

    private fun applySafeArea(root: View) {
        ViewCompat.setOnApplyWindowInsetsListener(root) { view, insets ->
            val bars = insets.getInsets(
                WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.displayCutout(),
            )
            view.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            WindowInsetsCompat.CONSUMED
        }
        ViewCompat.requestApplyInsets(root)
    }

    private fun seedFrameKey(tMs: Double): Int {
        val fps = max(prepareMeta?.fps ?: 30.0, 1.0)
        val frameMs = 1000.0 / fps
        return (tMs / frameMs).roundToInt()
    }

    private fun seedNear(tMs: Double): SeedMark? {
        var hit: SeedMark? = prepareSeeds[seedFrameKey(tMs)]
        if (hit != null) {
            return hit
        }
        var best = 40.0
        for (item in prepareSeeds.values) {
            val delta = kotlin.math.abs(item.tMs - tMs)
            if (delta <= best) {
                best = delta
                hit = item
            }
        }
        return hit
    }

    private fun syncPrepareKeyframes() {
        prepareTimeline.setKeyframes(prepareSeeds.values.map { it.tMs.toInt() })
    }

    private fun showBirthdayPicker() {
        DatePickerDialog(
            this,
            { _, year, month, day ->
                birthdayCal.set(year, month, day)
                refreshBirthdayLabel()
            },
            birthdayCal.get(Calendar.YEAR),
            birthdayCal.get(Calendar.MONTH),
            birthdayCal.get(Calendar.DAY_OF_MONTH),
        ).show()
    }

    private fun refreshBirthdayLabel() {
        val fmt = SimpleDateFormat(I18n.t("MM/dd/yyyy"), Locale.US)
        inputBirthday.text = fmt.format(birthdayCal.time)
    }

    private fun birthdayIso(): String {
        return String.format(
            Locale.US,
            "%04d-%02d-%02d",
            birthdayCal.get(Calendar.YEAR),
            birthdayCal.get(Calendar.MONTH) + 1,
            birthdayCal.get(Calendar.DAY_OF_MONTH),
        )
    }

    private fun currentProfileKey(): String {
        return (spinnerProfile.selectedItem as? ProfileOption)?.key.orEmpty()
    }

    private fun currentGender(): AthleteGender {
        return genderOrder.getOrElse(spinnerGender.selectedItemPosition) { AthleteGender.UNSPECIFIED }
    }

    private fun rebuildGenderSpinner() {
        val selected = currentGender()
        val labels = listOf(
            I18n.t("Unspecified"),
            I18n.t("Female"),
            I18n.t("Male"),
            I18n.t("Other"),
        )
        val adapter = ArrayAdapter(this, R.layout.spinner_item, labels)
        adapter.setDropDownViewResource(R.layout.spinner_item)
        spinnerGender.adapter = adapter
        spinnerGender.setSelection(genderOrder.indexOf(selected).coerceAtLeast(0), false)
    }

    private fun reloadProfiles(preserveKey: String?) {
        loadingProfile = true
        val options = ArrayList<ProfileOption>()
        options.add(ProfileOption("", I18n.t("New profile")))
        for (item in athletes.list()) {
            options.add(ProfileOption(item.key, item.key))
        }
        val adapter = ArrayAdapter(this, R.layout.spinner_item, options)
        adapter.setDropDownViewResource(R.layout.spinner_item)
        spinnerProfile.adapter = adapter
        val want = preserveKey.orEmpty()
        val idx = options.indexOfFirst { it.key == want }.coerceAtLeast(0)
        spinnerProfile.setSelection(idx, false)
        loadingProfile = false
    }

    private fun applyProfileKey(key: String) {
        val profile = athletes.getByKey(key) ?: return
        fillFromProfile(profile)
        loadingProfile = true
        val idx = (0 until spinnerProfile.count).firstOrNull { i ->
            (spinnerProfile.getItemAtPosition(i) as? ProfileOption)?.key == profile.key
        } ?: 0
        spinnerProfile.setSelection(idx, false)
        loadingProfile = false
    }

    private fun fillFromProfile(profile: AthleteProfile) {
        inputName.setText(profile.name)
        inputHeight.setText(Athletes.formatMeasure(profile.heightCm))
        inputWeight.setText(Athletes.formatMeasure(profile.weightKg))
        inputSki.setText(Athletes.formatMeasure(profile.skiCm))
        spinnerGender.setSelection(genderOrder.indexOf(profile.gender).coerceAtLeast(0), false)
        if (profile.birthday.isNotBlank()) {
            val parts = profile.birthday.split("-")
            if (parts.size >= 3) {
                val year = parts[0].toIntOrNull()
                val month = parts[1].toIntOrNull()
                val day = parts[2].toIntOrNull()
                if (year != null && month != null && day != null) {
                    birthdayCal.set(year, month - 1, day)
                }
            }
        } else {
            birthdayCal.set(1990, Calendar.JANUARY, 1)
        }
        refreshBirthdayLabel()
    }

    private fun readAthlete(): AthleteProfile? {
        val name = inputName.text.toString().trim()
        if (name.isEmpty()) {
            return null
        }
        val height = inputHeight.text.toString().toFloatOrNull() ?: return null
        val weight = inputWeight.text.toString().toFloatOrNull() ?: return null
        val ski = inputSki.text.toString().toFloatOrNull() ?: return null
        return try {
            athletes.upsert(
                name = name,
                weightKg = weight,
                heightCm = height,
                skiCm = ski,
                birthday = birthdayIso(),
                gender = currentGender(),
            )
        } catch (_: IllegalArgumentException) {
            null
        }
    }

    private fun MaterialButton.setIconOnly(label: String) {
        text = null
        contentDescription = label
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    private enum class Page { LIST, CAPTURE, PREPARE, PLAYER }

    private data class ProfileOption(val key: String, val label: String) {
        override fun toString(): String = label
    }

    companion object {
        private const val TAG = "CorePose"
        private val SPEEDS = floatArrayOf(0.5f, 0.75f, 1f, 1.25f, 1.5f, 2f)
    }
}
