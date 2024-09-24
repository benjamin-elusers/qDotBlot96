import sys
import logging
import numpy as np
import cv2
import csv
import os

from PySide6.QtWidgets import (QApplication, QMainWindow, QMenu, QWidget,  QStatusBar, 
                               QGroupBox, QVBoxLayout, QHBoxLayout, QSplitter, QSpinBox, 
                               QPushButton, QSlider, QFileDialog, QColorDialog, QLabel,  
                               QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsTextItem,
                               QListWidget,  QTableWidget, QTableWidgetItem, QToolBar )
from PySide6.QtCore import Qt, QLineF, QRectF, QPointF, QEvent
from PySide6.QtGui import QAction, QIcon, QImage, QPixmap, QPen, QColor, QPainter, QCursor, QFontDatabase
from PySide6.QtUiTools import QUiLoader
from qt_material import QtStyleTools, apply_stylesheet
import qtawesome as qta

# Constants
ROI_RADIUS = 15
SATURATION = 0.05
ROWS = 8
COLUMNS = 12
MAXINT16 = 65535.0
MAXINT8 = 255.0
COLOR_THEME = "#1de9b6"
ICON_OPTIONS = [{'scale_factor': 1.4, 'color' : COLOR_THEME }]

# Setup logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class RuntimeStylesheets(QMainWindow, QtStyleTools):

    def __init__(self):
        super().__init__()
        self.main = QUiLoader().load('main_window.ui', self)
        self.add_menu_theme(self.main, self.main.menuStyles)

class WellGridApp(QMainWindow):
    
    def __init__(self):
        logger.debug("Initializing WellGridApp.")
        super().__init__()
        self.setWindowTitle("Quantify 96-well dotblot")
        self.setGeometry(0, 0, 1920, 1360)

        # Initialize variables
        self.init_variables()

        # Setup main UI components
        self.setup_ui()

        # Create theme selection menu
        #self.setup_theme_menu()

        # Change the style of the UI
        #self.setStyleSheet(style)

        # Connect mouse events
        self.connect_mouse_events()

    def init_variables(self):
        """Initialize internal variables."""
        logger.debug("Initializing internal variables.")
        self.images = []
        self.image_paths = []
        self.current_image = None
        self.original_image = None
        self.roi_radius = ROI_RADIUS
        self.nrows, self.ncols = ROWS, COLUMNS
        self.grid_offset = [0, 0]
        self.grid_spacing = [0, 0]
        self.corners = []
        self.corner_points = []
        self.corner_lines = []
        self.circles = []
        self.labels = []
        self.measurements = []
        self.roi_color = QColor('red')
        self.saturation_fraction = SATURATION
        self.defining_grid = False
        self.grid_defined = False
        self.magnifier_item = None
        self.spacing_increment = 1

    def check_grid(self):
        logger.debug(f"ROI circles   : {len(self.circles)}")
        logger.debug(f"ROI labels    : {len(self.labels)}")
        logger.debug(f"corners       : {len(self.corners)}")
        logger.debug(f"corner lines  : {len(self.corner_lines)}")
        logger.debug(f"corner points : {len(self.corner_points)}")
        logger.debug(f"grid offset   : {self.grid_offset}")
        logger.debug(f"grid spacing  : {self.grid_spacing}")

    def setup_ui(self):
        """Setup the UI elements and layout."""
        logger.debug("Setting up UI components.")
        
        # Main layout as QSplitter
        main_layout = QSplitter(Qt.Orientation.Vertical)

        # Sidebar (left panel) with fixed width
        sidebar_widget = self.setup_sidebar()

        # Image widget
        image_widget = QWidget()
        image_widget.setFixedWidth(900)        
        image_group = QGroupBox("Image Section")
        image_layout = QVBoxLayout()
        
        # Add the toolbar for image controls
        image_layout.addWidget(self.setup_image_toolbar())  # Toolbar added to the top of the image section
        
        # Add scene for image display
        self.image_scene = QGraphicsScene()
        self.image_view = QGraphicsView(self.image_scene)  # Store image_view as a class attribute if needed elsewhere
        self.image_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.image_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.image_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        image_layout.addWidget(self.image_view)  # Only the image_view is added to the layout, not the scene itself
        
        image_group.setLayout(image_layout)
        image_widget_layout = QVBoxLayout()
        image_widget_layout.addWidget(image_group)
        image_widget.setLayout(image_widget_layout)

        # Measurement widget
        measurement_widget = QWidget()
        measurement_widget.setFixedWidth(720)
        measurement_layout = QVBoxLayout()
        measurement_group = QGroupBox("Measurements Section")
        
        # Add measurements table to measurements group
        measurement_group.setLayout(self.setup_measurements_table())  # Assuming this method returns a layout
        measurement_layout.addWidget(measurement_group)
        measurement_widget.setLayout(measurement_layout)

        # Splitter for sidebar and main view
        layout_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout_splitter.addWidget(sidebar_widget)
        layout_splitter.addWidget(image_widget)
        layout_splitter.addWidget(measurement_widget)

        # Set the splitter's stretch factor so the sidebar doesn't resize
        layout_splitter.setStretchFactor(0, 0)  # Sidebar fixed
        layout_splitter.setStretchFactor(1, 1)  # Image section resizable
        layout_splitter.setStretchFactor(2, 0)  # Measurements table resizable

        # Set the central widget as the splitter layout
        self.setCentralWidget(layout_splitter)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def setup_theme_menu(self):
        """Create a menu for selecting themes."""
        logger.debug("Creating theme selection menu.")

        # Create a menu bar
        menu_bar = self.menuBar()

        # Add a "Themes" menu
        themes_menu = QMenu("Themes", self)
        menu_bar.addMenu(themes_menu)

        # List of available themes in qt-material
        available_themes = [
            'dark_blue.xml', 'dark_cyan.xml', 'dark_lightgreen.xml', 'dark_pink.xml',
            'dark_purple.xml', 'dark_red.xml', 'dark_teal.xml', 'dark_yellow.xml'
        ]

        # Create actions for each theme
        for theme in available_themes:
            theme_action = QAction(theme.replace(".xml", "").replace("_", " ").capitalize(), self)
            theme_action.triggered.connect(lambda checked=False, t=theme: self.apply_theme(t))
            themes_menu.addAction(theme_action)

    def apply_theme(self, theme):
        """Apply the selected theme."""
        logger.info(f"Applying theme: {theme}")
        apply_stylesheet(app, theme=theme, extra=extra)

    def setup_sidebar(self):
        """Setup the sidebar with control sections for image, grid, and measurements."""
        logger.debug("Setting up sidebar layout.")
        sidebar_widget = QWidget()
        # Fix the width of the sidebar
        sidebar_widget.setFixedWidth(250)
        sidebar_layout = QVBoxLayout()

        # Image controls
        image_group = QGroupBox("Image Controls")
        image_group.setFixedHeight(200)
        image_layout = QVBoxLayout()
        self.setup_image_controls(image_layout)
        image_group.setLayout(image_layout)

        # Grid controls
        grid_group = QGroupBox("Grid Controls")
        grid_layout = QVBoxLayout()
        self.setup_grid_controls(grid_layout)
        grid_group.setLayout(grid_layout)

        # Measurements controls
        measurements_group = QGroupBox("Measurements Controls")
        measurements_layout = QVBoxLayout()
        self.setup_measurement_controls(measurements_layout)
        measurements_group.setLayout(measurements_layout)

        # Add each section to the sidebar layout
        sidebar_layout.addWidget(image_group)
        sidebar_layout.addWidget(grid_group)
        sidebar_layout.addWidget(measurements_group)

        # Set layout for sidebar widget
        sidebar_widget.setLayout(sidebar_layout)

        return sidebar_widget

    def setup_image_toolbar(self):
        """Setup the toolbar with image manipulation tools."""
        # Create a toolbar specifically for the image section
        image_toolbar = QToolBar("Image Tools", self)

        # Save button with icon        
        save_icon = qta.icon('mdi6.content-save', options=ICON_OPTIONS)
        save_button = QPushButton(save_icon, "Save")
        save_button.clicked.connect(self.save_image)
        image_toolbar.addWidget(save_button)

        # Zoom in button with icon
        zoomin_icon = qta.icon('mdi6.magnify-plus', options=ICON_OPTIONS)
        zoom_in_button = QPushButton(zoomin_icon, "Zoom In")
        zoom_in_button.clicked.connect(self.zoom_in)
        image_toolbar.addWidget(zoom_in_button)

        # Zoom out button with icon
        zoomout_icon = qta.icon('mdi6.magnify-minus', options=ICON_OPTIONS)
        zoom_out_button = QPushButton(zoomout_icon, "Zoom Out")
        zoom_out_button.clicked.connect(self.zoom_out)
        image_toolbar.addWidget(zoom_out_button)

        # Pan button with icon
        pan_icon = qta.icon('mdi6.pan', options=ICON_OPTIONS)
        pan_button = QPushButton(pan_icon, "Pan")
        pan_button.clicked.connect(self.toggle_pan_mode)
        image_toolbar.addWidget(pan_button)

        return image_toolbar

    def setup_image_controls(self, layout):
        """Setup image loading and saturation controls."""
        logger.debug("Setting up image controls.")
        # Load image button
        self.load_button = QPushButton("Load Image")
        self.load_button.clicked.connect(self.load_image)
        layout.addWidget(self.load_button)

        # Image list widget
        self.image_list = QListWidget()
        self.image_list.itemClicked.connect(self.show_image)
        layout.addWidget(self.image_list)

        # Saturation slider
        layout.addWidget(QLabel("Saturation"))
        self.saturation_slider = QSlider(Qt.Orientation.Horizontal)
        self.saturation_slider.setRange(0, 1000)
        self.saturation_slider.setValue(SATURATION * 10)
        self.saturation_slider.valueChanged.connect(self.adjust_saturation)
        layout.addWidget(self.saturation_slider)

    def setup_grid_controls(self, layout):
        """Setup grid adjustment controls."""
        logger.debug("Setting up grid controls.")
        # Define grid button
        self.define_grid_button = QPushButton("Define Grid")
        self.define_grid_button.clicked.connect(self.toggle_define_grid_mode)
        layout.addWidget(self.define_grid_button)

        # ROI radius slider
        layout.addWidget(QLabel("ROI Radius"))
        self.roi_radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.roi_radius_slider.setRange(15, 30)
        self.roi_radius_slider.setValue(ROI_RADIUS)
        self.roi_radius_slider.valueChanged.connect(self.adjust_roi_radius)
        layout.addWidget(self.roi_radius_slider)

        # Color change button
        self.color_button = QPushButton("Change ROI Color")
        self.color_button.clicked.connect(self.change_roi_color)
        layout.addWidget(self.color_button)

        # Grid movement buttons
        self.setup_grid_movement_buttons(layout)

    def setup_measurements_table(self):
        logger.debug("Setting up measurement table.")
        """Setup the measurements section."""
        # Initialize the measurements table
        measurements_layout = QVBoxLayout()
        self.measurements_table = QTableWidget()
        measurements_layout.addWidget(self.measurements_table)
        return measurements_layout

    def setup_measurement_controls(self, layout):
        """Setup measurement controls."""
        logger.debug("Setting up measurement controls.")
        # Measure grid button
        self.measure_button = QPushButton("Measure Grid")
        self.measure_button.clicked.connect(self.measure_grid)
        layout.addWidget(self.measure_button)

        # Save as CSV button
        self.save_button = QPushButton("Save as CSV")
        self.save_button.clicked.connect(self.save_csv)
        layout.addWidget(self.save_button)

        # Reset button
        self.reset_button = QPushButton("Reset")
        self.reset_button.clicked.connect(self.reset_app)
        layout.addWidget(self.reset_button)

    def connect_mouse_events(self):
        """Connect mouse move event to track coordinates."""
        self.image_view.viewport().setMouseTracking(True)
        self.image_view.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        """Filter mouse events to update the magnifier and status bar."""
        if event.type() == QEvent.Type.MouseMove and self.current_image is not None:
            pos = event.position()
            scene_pos = self.image_view.mapToScene(pos.toPoint())  # Convert QPointF to QPoint
            x, y = int(scene_pos.x()), int(scene_pos.y())
            is_cursor_inframe = (0 <= x < self.current_image.shape[1] and 0 <= y < self.current_image.shape[0])

            if is_cursor_inframe:
                self.update_status_bar(x, y)
                if self.defining_grid:
                    self.update_magnifier(x, y)
            if self.defining_grid and not is_cursor_inframe and self.magnifier_item:
                self.image_scene.removeItem(self.magnifier_item)
                self.magnifier_item = None

        return super().eventFilter(obj, event)
    
    def on_mouse_press(self, event):
        """Handle mouse press to define grid corners."""
        if len(self.corners) < 3 and self.defining_grid:
            scene_pos = self.image_view.mapToScene(event.position().toPoint())
            self.corners.append((scene_pos.x(), scene_pos.y()))

            corner_ellipse = QGraphicsEllipseItem(scene_pos.x() - 5, scene_pos.y() - 5, 10, 10)
            corner_ellipse.setPen(QPen(Qt.GlobalColor.red))
            corner_ellipse.setBrush(QColor(Qt.GlobalColor.red))

            self.image_scene.addItem(corner_ellipse)
            self.corner_points.append(corner_ellipse)

            if len(self.corners) == 3:
                self.grid_defined = True
                self.defining_grid = False
                self.define_grid_button.setText("Define Grid")
                self.image_view.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
                self.image_view.mousePressEvent = None
                if self.magnifier_item:
                    self.image_scene.removeItem(self.magnifier_item)
                    self.magnifier_item = None
                self.draw_orientation_lines()
                self.draw_grid()

    ###############
    #### IMAGE ####
    ###############

    def load_image(self):
        """Load and display an image."""
        logger.info("Loading image.")
        file_dialog = QFileDialog(self)
        file_path, _ = file_dialog.getOpenFileName(self, "Open Image", "", "Image Files (*.png *.jpg *.tif)")
        if file_path:
            self.image_paths.append(file_path)
            img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
            if img.dtype != np.uint16:
                img = cv2.convertScaleAbs(img, alpha=(MAXINT16 / MAXINT8))
                img = img.astype(np.uint16)
            self.images.append(img)
            self.image_list.addItem(os.path.basename(file_path))

            if len(self.images) == 1:
                self.image_list.setCurrentRow(0)
                self.show_image()

    def show_image(self):
        """Display the selected image."""
        logger.info("Displaying image.")
        selected_idx = self.image_list.currentRow()
        if selected_idx >= 0:
            self.current_image = self.images[selected_idx]
            self.original_image = self.current_image.copy()
            self.update_image()

    def update_image(self):
        """Update the displayed image after any changes."""
        logger.debug("Updating image.")
        if self.current_image is not None:
            adjusted_image = self.adjust_image(self.current_image)
            height, width = adjusted_image.shape
            bytes_per_line = width * 2
            q_image = QImage(adjusted_image.data, width, height, bytes_per_line, QImage.Format.Format_Grayscale16)
            pixmap = QPixmap.fromImage(q_image)
            self.image_scene.clear()
            self.image_scene.addPixmap(pixmap)
            self.image_view.setSceneRect(QRectF(pixmap.rect()))
            self.update_grid()

    def zoom_in(self):
        """Zoom in the image."""
        self.image_view.scale(1.25, 1.25)  # Increase the zoom by 25%
        self.image_view.setDragMode(QGraphicsView.ScrollHandDrag)

    def zoom_out(self):
        """Zoom out the image."""
        self.image_view.scale(0.8, 0.8)  # Decrease the zoom by 20%
        self.image_view.setDragMode(QGraphicsView.ScrollHandDrag)

    def toggle_pan_mode(self):
        """Toggle the pan mode for moving around the image."""
        if self.image_view.dragMode() == QGraphicsView.ScrollHandDrag:
            self.image_view.setDragMode(QGraphicsView.NoDrag)
        else:
            self.image_view.setDragMode(QGraphicsView.ScrollHandDrag)

    def save_image(self):
        """Save the current displayed image with any painted objects."""
        if not self.image_paths:
            return

        current_image_path = self.image_paths[self.image_list.currentRow()]
        folder, filename_with_ext = os.path.split(current_image_path)  # Splits path into folder and filename
        filename, ext = os.path.splitext(filename_with_ext)  # Splits filename into name and extension
        dotblot_image = os.path.join(folder, f"dotblot-{filename}{ext}")

        file_dialog = QFileDialog(self)
        file_path, _ = file_dialog.getSaveFileName(self, "Save Image",  dotblot_image, "PNG Files (*.png);;JPG Files (*.jpg);;TIFF Files (*.tif);;")
        if file_path:
            # Convert QGraphicsScene to image
            image = QImage(self.image_view.viewport().size(), QImage.Format_ARGB32)
            painter = QPainter(image)
            self.image_view.render(painter)
            painter.end()
            image.save(file_path)
            logger.info(f"Image saved to {file_path}")

    def set_spacing_increment(self, value):
        """Set the grid spacing increment from the user input."""
        logger.debug("Adjusting spacing increment.")
        self.spacing_increment = value

    def adjust_image(self, image):
        """Adjust the image based on the saturation settings."""
        logger.debug("Adjusting image saturation.")
        v_min, v_max = np.percentile(image, (0, 100 - self.saturation_fraction * 100))
        return np.clip((image - v_min) * MAXINT16 / (v_max - v_min), 0, MAXINT16).astype(np.uint16)

    def adjust_saturation(self, value):
        """Adjust image saturation and refresh."""
        logger.debug(f"Adjusting saturation to {value}.")
        self.saturation_fraction = value / 1000.0
        self.update_image()

    def update_status_bar(self, x, y):
        """Update the status bar with the current cursor position and intensity."""
        logger.debug(f"Updating status bar for position: ({x}, {y}).")
        if self.current_image is None:
            return
        else:
            adjusted_image = self.adjust_image(self.current_image)
            intensity = adjusted_image[y, x]
            max_intensity = np.max(adjusted_image)
            relative_intensity = (intensity / max_intensity) * 100
            percentile_intensity = (intensity / MAXINT16) * 100

            self.status_bar.showMessage(f"X: {x}, Y: {y} | Intensity: {intensity} | "
                                        f"Relative: {relative_intensity:.2f}% | "
                                        f"Percentile: {percentile_intensity:.2f}%")

    def update_magnifier(self, x, y):
        """Update magnifier view at the current cursor position."""
        logger.debug(f"Updating magnifier at position: ({x}, {y}).")
        if self.current_image is None:
            return
        else:
            adjusted_image = self.adjust_image(self.current_image)
            region_size = 30
            zoom_factor = 3

            x_min, x_max = max(0, x - region_size), min(adjusted_image.shape[1], x + region_size)
            y_min, y_max = max(0, y - region_size), min(adjusted_image.shape[0], y + region_size)

            region = adjusted_image[y_min:y_max, x_min:x_max]
            region_resized = cv2.resize(region, (region.shape[1] * zoom_factor, region.shape[0] * zoom_factor),
                                        interpolation=cv2.INTER_NEAREST)

            # Create circular mask
            mask = np.zeros_like(region_resized)
            center = (region_resized.shape[1] // 2, region_resized.shape[0] // 2)
            radius = region_size * zoom_factor
            cv2.circle(mask, center, radius, MAXINT16, thickness=-1)

            region_resized = cv2.bitwise_and(region_resized, mask)

            height, width = region_resized.shape
            bytes_per_line = width * 2
            q_image = QImage(region_resized.data, width, height, bytes_per_line, QImage.Format.Format_Grayscale16)
            pixmap = QPixmap.fromImage(q_image)

            if self.magnifier_item:
                self.image_scene.removeItem(self.magnifier_item)
                self.magnifier_item = None

            self.magnifier_item = self.image_scene.addPixmap(pixmap)
            self.magnifier_item.setPos(x - region_size * zoom_factor, y - region_size * zoom_factor)
            self.magnifier_item.setZValue(1000)

    ##############
    #### GRID ####
    ##############

    def setup_adjustment_buttons(self, layout, label, direction):
        """Setup buttons for adjusting grid width or height."""
        logger.debug(f"Setting up grid {label} adjustment buttons.")
        adjust_layout = QHBoxLayout()
        adjust_layout.addWidget(QLabel(f"{label}: "))

        increase_button = QPushButton("+") # ➕ Heavy sign  # ＋ fullwidth
        increase_button.clicked.connect(lambda: self.adjust_grid_spacing(direction, self.spacing_increment))
        adjust_layout.addWidget(increase_button)

        decrease_button = QPushButton("−") # ➖ Heavy sign 
        decrease_button.clicked.connect(lambda: self.adjust_grid_spacing(direction, -self.spacing_increment))
        adjust_layout.addWidget(decrease_button)

        layout.addLayout(adjust_layout)

    def setup_grid_movement_buttons(self, layout):
        """Setup grid movement buttons."""
        logger.debug("Setting up grid movement buttons.")
        # Translate Grid Section
        layout.addWidget(QLabel("Translate Grid"))

        button_layout = QVBoxLayout()
        # Create grid movement buttons in a cross layout

        # Empty widget to create space between left and right
        empty_label = QLabel(" ")

        # TOP
        top_layout = QHBoxLayout()
        top_layout.addWidget(empty_label)
        # Up button
        self.up_button = QPushButton("↑")
        self.up_button.clicked.connect(lambda: self.move_grid(0, -1))
        top_layout.addWidget(self.up_button)
        top_layout.addWidget(empty_label)

        # CENTER
        # Center part of the cross layout (empty to leave space for left-right buttons)
        center_layout = QHBoxLayout()
        # Left button
        self.left_button = QPushButton("←")
        self.left_button.clicked.connect(lambda: self.move_grid(-1, 0))
        center_layout.addWidget(self.left_button)
        center_layout.addWidget(empty_label)
        # Right button
        self.right_button = QPushButton("→")
        self.right_button.clicked.connect(lambda: self.move_grid(1, 0))
        center_layout.addWidget(self.right_button)

        # BOTTOM
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(empty_label)
        # Down button
        self.down_button = QPushButton("↓")
        self.down_button.clicked.connect(lambda: self.move_grid(0, 1))
        bottom_layout.addWidget(self.down_button)
        bottom_layout.addWidget(empty_label)

        button_layout.addLayout(top_layout)
        button_layout.addLayout(center_layout)
        button_layout.addLayout(bottom_layout)

        # Add the button layout to the sidebar or the parent layout
        layout.addLayout(button_layout)

        # Spacing controls
        layout.addWidget(QLabel("Spacing Increment:"))
        self.spacing_increment_input = QSpinBox()
        self.spacing_increment_input.setRange(1, 20)
        self.spacing_increment_input.setValue(1)
        self.spacing_increment_input.setStyleSheet("QSpinBox { color: white; }")

        self.spacing_increment_input.valueChanged.connect(self.set_spacing_increment)
        layout.addWidget(self.spacing_increment_input)

        # Width and height adjustment buttons
        self.setup_adjustment_buttons(layout, "Width", 'width')
        self.setup_adjustment_buttons(layout, "Height", 'height')

    def update_grid(self):
        self.erase_grid()
        self.draw_orientation_lines()
        self.draw_grid()

    def remove_scene_items(self, items):
        """Safely remove items from the scene."""
        logger.debug("Removing scene items.")
        for item in items[:]:  # Iterate over a copy of the list to avoid modifying it during iteration
            if item and item.scene():  # Ensure the item still exists in the scene
                self.image_scene.removeItem(item)  # Remove item from the scene

    def clear_scene_items(self, items):
        """Safely remove items from the scene and clear the list."""
        logger.debug("Clearing scene items.")
        self.remove_scene_items(items)
        items.clear()  # Clear the list after all items are removed

    def adjust_roi_radius(self, value):
        """Adjust the ROI radius and refresh the image."""
        logger.debug(f"Setting ROI radius to {value}.")
        self.roi_radius = value
        self.update_grid()

    def change_roi_color(self):
        """Open a color dialog to change the ROI color."""
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            logger.debug(f"Setting ROI color to {color}.")
            self.roi_color = color
            self.update_grid()

    def toggle_define_grid_mode(self):
        """Toggle grid definition mode."""
        logger.info("Toggling grid definition mode.")
        if self.defining_grid:
            logger.info("--> Already defining grid.")
            self.reset_define_grid()
        else:
            if self.grid_defined:
                logger.info("--> Grid was defined already.")
                self.reset_grid()
            else:
                logger.info("--> No previous grid defined.")
            self.define_grid()
            print("")

    def define_grid(self):
        """Start defining the grid by selecting corners."""
        logger.info("--> Grid definition mode activated.")
        if self.current_image is None:
            return
        self.reset_grid()
        self.grid_defined = False
        self.defining_grid = True
        self.define_grid_button.setText("Cancel Grid Definition")
        self.image_view.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        self.image_view.mousePressEvent = self.on_mouse_press

    def reset_define_grid(self):
        """Reset the grid definition mode."""
        logger.info("--> Resetting grid definition mode.")
        self.reset_grid()
        self.defining_grid = False
        self.define_grid_button.setText("Define Grid")
        self.image_view.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.image_view.mousePressEvent = None

    def erase_grid(self):
        """Erase the grid items from the scene."""
        self.remove_scene_items(self.circles)
        self.remove_scene_items(self.labels)
        self.remove_scene_items(self.corner_lines)
        self.remove_scene_items(self.corner_points)

    def remove_grid(self):
        """Erase the grid items from the scene."""
        self.erase_grid()
        self.circles.clear()
        self.labels.clear()
        self.corner_lines.clear()
        self.corner_points.clear()
        self.corners.clear()

    def reset_grid(self):
        """Reset the grid and clear only the grid-related items from the scene."""
        logger.info("Resetting grid.")
        if self.grid_defined:
            logger.info("Removing existing grid.")
            self.grid_defined = False
            self.check_grid()
            self.remove_grid()
            self.check_grid()
        self.image_scene.update()

    def adjust_grid_spacing(self, direction, value):
        """Adjust the grid spacing by increasing or decreasing row/column spacing."""
        logger.debug(f"Adjusting grid {direction} by {value}.")
        if direction == 'width':
            self.grid_spacing[0] += value  # Adjust only width
            self.grid_spacing[1] = 0  # Reset the height adjustment to 0
        elif direction == 'height':
            self.grid_spacing[0] = 0   # Reset the width adjustment to 0
            self.grid_spacing[1] += value  # Adjust only height
        self.check_grid()
        self.update_grid()  # Redraw the grid with updated spacing

    def move_grid(self, dx, dy):
        """Move the entire grid by adjusting the offset."""
        logger.debug(f"Moving grid by dx={dx}, dy={dy}.")
        self.grid_offset[0] += dx #* self.grid_spacing[0]
        self.grid_offset[1] += dy #* self.grid_spacing[1]
        self.update_grid()  # Redraw the grid with updated offset

    def draw_orientation_lines(self):
        """Draw orientation lines between grid corners."""
        if len(self.corners) == 3:
            logger.debug("Draw the corner orientation lines.")
            a1, a12, h1 = self.corners
            
            self.corner_lines = []
            hline = QGraphicsLineItem(QLineF(a1[0], a1[1], a12[0], a12[1]))
            hline.setPen(QPen(Qt.GlobalColor.yellow, 2))
            self.image_scene.addItem(hline)
            self.corner_lines.append(hline)

            vline = QGraphicsLineItem(QLineF(a1[0], a1[1], h1[0], h1[1]))
            vline.setPen(QPen(Qt.GlobalColor.yellow, 2))
            self.image_scene.addItem(vline)
            self.corner_lines.append(vline)

    def draw_grid(self):
        """Draw the grid based on defined corners and grid offset/spacing."""
        logger.debug("Drawing grid.")
        if len(self.corners) != 3:
            return

        a1, a12, h1 = np.array(self.corners[0]), np.array(self.corners[1]), np.array(self.corners[2])

        # Adjust the row and column vectors based on grid_spacing
        row_vec = (h1 - a1) / (self.nrows - 1)
        col_vec = (a12 - a1) / (self.ncols - 1)

        # Apply the grid offset (translation)
        a1 += np.array(self.grid_offset)

        # Clear the scene and reset the tracking lists
        self.circles = []
        self.labels = []

        # Redraw the grid
        for i in range(self.nrows):
            for j in range(self.ncols):
                # Compute the center, applying grid_spacing[0] to x (column) and grid_spacing[1] to y (row)
                center = a1 + i * (row_vec + [0, self.grid_spacing[1]]) + j * (col_vec + [self.grid_spacing[0], 0])

                # Draw the circle
                circ = QGraphicsEllipseItem(center[0] - self.roi_radius, center[1] - self.roi_radius,
                                            2 * self.roi_radius, 2 * self.roi_radius)
                circ.setPen(QPen(self.roi_color))
                self.circles.append(circ)  # Add circle to the list

                # Get the well name (3-character long)
                well_name = self.get_well_name(i, j)

                # Create text item and center it on the circle
                text = QGraphicsTextItem(well_name)
                text_width = text.boundingRect().width()
                text_height = text.boundingRect().height()
                text.setPos(center[0] - text_width / 2, center[1] - text_height / 2)
                text.setDefaultTextColor(self.roi_color)
                self.labels.append(text)  # Add label to the list

        # Add the circles and labels to the scene
        for c in self.circles:
            self.image_scene.addItem(c)

        for t in self.labels:
            self.image_scene.addItem(t)

    def get_well_name(self, row, col):
        """Get well name based on row and column indices."""
        letter = chr(ord('A') + row)
        number = f"{col + 1:02}"
        return f"{letter}{number}"

    def measure_grid(self):
        """Measure the grid wells and collect intensity data."""
        logger.info("Measuring grid intensities.")
        if self.current_image is None or len(self.circles) == 0:
            return

        self.measurements = []
        for i, circ in enumerate(self.circles):
            if circ:  # Check if the circle item is still valid
                center = circ.rect().center()
                center_x, center_y = int(center.x()), int(center.y())
                radius = int(self.roi_radius)

                x_min, x_max = max(0, center_x - radius), min(self.current_image.shape[1], center_x + radius)
                y_min, y_max = max(0, center_y - radius), min(self.current_image.shape[0], center_y + radius)

                roi_pixels = self.current_image[y_min:y_max, x_min:x_max]
                mean_intensity = np.mean(roi_pixels)
                median_intensity = np.median(roi_pixels)
                std_dev = np.std(roi_pixels)
                mode = np.argmax(np.bincount(roi_pixels.ravel()))
                min_intensity = np.min(roi_pixels)
                max_intensity = np.max(roi_pixels)

                self.measurements.append({
                    'well': self.get_well_name(i // self.ncols, i % self.ncols),
                    'x_center': center_x,
                    'y_center': center_y,
                    'median': int(median_intensity),
                    'mean': round(mean_intensity, 1),
                    'stdev': round(std_dev, 1),
                    'mode': int(mode),
                    'min': int(min_intensity),
                    'max': int(max_intensity)
                })

        self.update_measurements_table()


    def update_measurements_table(self):
        """Update the measurements table with new data."""
        logger.debug("Updating measurements table.")
        if not self.measurements:
            return

        self.measurements_table.setColumnCount(len(self.measurements[0]))
        self.measurements_table.setRowCount(len(self.measurements))

        headers = list(self.measurements[0].keys())
        self.measurements_table.setHorizontalHeaderLabels(headers)

        for i, measurement in enumerate(self.measurements):
            for j, (key, value) in enumerate(measurement.items()):
                self.measurements_table.setItem(i, j, QTableWidgetItem(str(value)))

        self.measurements_table.resizeColumnsToContents()

    def save_csv(self):
        """Save the measurements to a CSV file."""
        logger.info("Saving measurements to CSV.")
        if not self.measurements or not self.image_paths:
            return

        current_image_path = self.image_paths[self.image_list.currentRow()]
        default_csv_path = os.path.splitext(current_image_path)[0] + ".csv"

        file_dialog = QFileDialog(self)
        file_path, _ = file_dialog.getSaveFileName(self, "Save CSV", default_csv_path, "CSV Files (*.csv)")
        if file_path:
            with open(file_path, mode='w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=self.measurements[0].keys())
                writer.writeheader()
                writer.writerows(self.measurements)
            logger.info(f"Measurements saved to {file_path}")

    def reset_app(self):
        """Reset the application to its initial state."""
        logger.info("Resetting the application.")
        self.init_variables()
        self.image_list.clear()
        self.image_scene.clear()
        self.measurements_table.clear()
        self.measurements_table.setRowCount(0)
        self.measurements_table.setColumnCount(0)
        logger.info("App has been reset to its initial state.")


if __name__ == "__main__":
    logger.debug("Starting WellGridApp.")
    app = QApplication(sys.argv)
    # setup stylesheet
    extra = {
        # Density Scale
        'density_scale': '-1',
        'font_size': '16px',
        'QLabel' : { 'font-size': '50px' }
    }
    apply_stylesheet(app, theme='dark_teal.xml', extra=extra)
    window = WellGridApp()
    window.show()
    sys.exit(app.exec())