"""
OpenCV Lane Departure Warning Tracker
Input: Video stream / Camera frame
Output: Lane deviation offset (meters), LDW status flag

(C) 2026 Alexandre Teixeira
"""

import cv2
import numpy as np

class LDWTracker:
    def __init__(self, frame_width=1280, frame_height=720):
        self.w = frame_width
        self.h = frame_height
        
        # Exponential moving average buffers for polynomial smooth fit
        self.left_a, self.left_b, self.left_c = [], [], []
        self.right_a, self.right_b, self.right_c = [], [], []

    def pipeline(self, img, s_thresh=(100, 255), sx_thresh=(15, 255)):
        """Converts RGB image to HLS space & extracts Sobel X and S-channel threshold binary."""
        hls = cv2.cvtColor(img, cv2.COLOR_BGR2HLS).astype(float)
        l_channel = hls[:, :, 1]
        s_channel = hls[:, :, 2]

        # Sobel x gradient
        sobelx = cv2.Sobel(l_channel, cv2.CV_64F, 1, 1)
        abs_sobelx = np.absolute(sobelx)
        max_sobel = np.max(abs_sobelx) if np.max(abs_sobelx) > 0 else 1
        scaled_sobel = np.uint8(255 * abs_sobelx / max_sobel)

        sxbinary = np.zeros_like(scaled_sobel)
        sxbinary[(scaled_sobel >= sx_thresh[0]) & (scaled_sobel <= sx_thresh[1])] = 1

        s_binary = np.zeros_like(s_channel)
        s_binary[(s_channel >= s_thresh[0]) & (s_channel <= s_thresh[1])] = 1

        combined_binary = np.zeros_like(sxbinary)
        combined_binary[(s_binary == 1) | (sxbinary == 1)] = 1
        return combined_binary

    def perspective_warp(self, img, 
                         src=np.float32([(0.43, 0.65), (0.58, 0.65), (0.1, 1.0), (1.0, 1.0)]),
                         dst=np.float32([(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)])):
        """Warps perspective to a bird's-eye top-down view."""
        img_size = np.float32([(self.w, self.h)])
        src_pts = src * img_size
        dst_pts = dst * np.float32((self.w, self.h))
        
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        return cv2.warpPerspective(img, M, (self.w, self.h))

    def inv_perspective_warp(self, img, 
                             src=np.float32([(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)]),
                             dst=np.float32([(0.43, 0.65), (0.58, 0.65), (0.1, 1.0), (1.0, 1.0)])):
        """Un-warps top-down perspective back to driver camera view."""
        img_size = np.float32([(self.w, self.h)])
        src_pts = src * img_size
        dst_pts = dst * np.float32((self.w, self.h))
        
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        return cv2.warpPerspective(img, M, (self.w, self.h))

    def sliding_window_tracking(self, binary_warped, nwindows=9, margin=100, minpix=50):
        """Finds lane line pixels using sliding window histogram peaks."""
        histogram = np.sum(binary_warped[binary_warped.shape[0] // 2:, :], axis=0)
        midpoint = int(histogram.shape[0] / 2)
        leftx_current = np.argmax(histogram[:midpoint])
        rightx_current = np.argmax(histogram[midpoint:]) + midpoint

        window_height = int(binary_warped.shape[0] / nwindows)
        nonzero = binary_warped.nonzero()
        nonzeroy = np.array(nonzero[0])
        nonzerox = np.array(nonzero[1])

        left_lane_inds = []
        right_lane_inds = []

        for window in range(nwindows):
            win_y_low = binary_warped.shape[0] - (window + 1) * window_height
            win_y_high = binary_warped.shape[0] - window * window_height
            
            win_xleft_low = leftx_current - margin
            win_xleft_high = leftx_current + margin
            win_xright_low = rightx_current - margin
            win_xright_high = rightx_current + margin

            good_left = ((nonzeroy >= win_y_low) & (nonzeroy < win_y_high) &
                        (nonzerox >= win_xleft_low) & (nonzerox < win_xleft_high)).nonzero()[0]
            good_right = ((nonzeroy >= win_y_low) & (nonzeroy < win_y_high) &
                         (nonzerox >= win_xright_low) & (nonzerox < win_xright_high)).nonzero()[0]

            left_lane_inds.append(good_left)
            right_lane_inds.append(good_right)

            if len(good_left) > minpix:
                leftx_current = int(np.mean(nonzerox[good_left]))
            if len(good_right) > minpix:
                rightx_current = int(np.mean(nonzerox[good_right]))

        left_lane_inds = np.concatenate(left_lane_inds)
        right_lane_inds = np.concatenate(right_lane_inds)

        leftx, lefty = nonzerox[left_lane_inds], nonzeroy[left_lane_inds]
        rightx, righty = nonzerox[right_lane_inds], nonzeroy[right_lane_inds]

        if len(leftx) == 0 or len(rightx) == 0:
            return None, None

        # Fit 2nd order polynomials
        left_fit = np.polyfit(lefty, leftx, 2)
        right_fit = np.polyfit(righty, rightx, 2)

        # Buffer smooth average over last 10 frames
        self.left_a.append(left_fit[0]); self.left_b.append(left_fit[1]); self.left_c.append(left_fit[2])
        self.right_a.append(right_fit[0]); self.right_b.append(right_fit[1]); self.right_c.append(right_fit[2])

        left_fit_avg = [np.mean(self.left_a[-10:]), np.mean(self.left_b[-10:]), np.mean(self.left_c[-10:])]
        right_fit_avg = [np.mean(self.right_a[-10:]), np.mean(self.right_b[-10:]), np.mean(self.right_c[-10:])]

        ploty = np.linspace(0, self.h - 1, self.h)
        left_fitx = left_fit_avg[0] * ploty**2 + left_fit_avg[1] * ploty + left_fit_avg[2]
        right_fitx = right_fit_avg[0] * ploty**2 + right_fit_avg[1] * ploty + right_fit_avg[2]

        return left_fitx, right_fitx

    def draw_lanes(self, img_bgr, left_fitx, right_fitx):
        """Draws green/red polygon overlay on original camera view."""
        ploty = np.linspace(0, self.h - 1, self.h)
        color_img = np.zeros_like(img_bgr)

        left = np.array([np.transpose(np.vstack([left_fitx, ploty]))])
        right = np.array([np.flipud(np.transpose(np.vstack([right_fitx, ploty])))])
        points = np.hstack((left, right))

        # Fill green polygon
        cv2.fillPoly(color_img, np.int_(points), (0, 255, 0))
        inv_perspective = self.inv_perspective_warp(color_img)
        return cv2.addWeighted(img_bgr, 1.0, inv_perspective, 0.4, 0)

    def process_frame(self, frame_bgr, ldw_threshold_m=0.45):
        """
        Main processing method for live frames.
        Returns: (overlay_bgr_frame, offset_meters, ldw_flag)
        ldw_flag: 0 = Safe, 1 = Left Drift, 2 = Right Drift
        """
        # Resize frame to standard pipeline resolution if needed
        if frame_bgr.shape[1] != self.w or frame_bgr.shape[0] != self.h:
            frame_bgr = cv2.resize(frame_bgr, (self.w, self.h))

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        binary = self.pipeline(frame_rgb)
        warped = self.perspective_warp(binary)
        left_fitx, right_fitx = self.sliding_window_tracking(warped)

        if left_fitx is None or right_fitx is None:
            return frame_bgr, 0.0, 0  # Return unmodified frame if lane lock is lost

        xm_per_pix = 3.7 / 700  # meters per pixel in x dimension
        car_pos = self.w / 2.0
        
        # Calculate offset from center
        lane_center = (left_fitx[-1] + right_fitx[-1]) / 2.0
        offset_meters = (car_pos - lane_center) * xm_per_pix

        # Evaluate Lane Departure Warning Status
        ldw_flag = 0
        if offset_meters > ldw_threshold_m:
            ldw_flag = 2  # Right Drift
        elif offset_meters < -ldw_threshold_m:
            ldw_flag = 1  # Left Drift

        # Draw visual overlay on video output
        annotated_frame = self.draw_lanes(frame_bgr, left_fitx, right_fitx)

        return annotated_frame, round(offset_meters, 3), ldw_flag

if __name__ == "__main__":
    # Supply either camera index (0) OR local video path
    VIDEO_SOURCE = "test_videos/highway_test.mp4" 

    cap = cv2.VideoCapture(VIDEO_SOURCE)

    if not cap.isOpened():
        print(f"[LDW Error] Could not open video source: {VIDEO_SOURCE}")
        exit()

    tracker = LDWTracker(frame_width=1280, frame_height=720)
    print(f"[LDW System] Processing source: {VIDEO_SOURCE}... Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[LDW] Video finished or frame stream ended.")
            break

        # Process frame through vision pipeline
        annotated_frame, offset, ldw_code = tracker.process_frame(frame)

        # On-screen visual status
        status_text = "CENTERED"
        color = (0, 255, 0)
        if ldw_code == 1:
            status_text = "WARNING: DRIFT LEFT"
            color = (0, 0, 255)
        elif ldw_code == 2:
            status_text = "WARNING: DRIFT RIGHT"
            color = (0, 0, 255)

        cv2.putText(annotated_frame, f"Offset: {offset:.3f} m", (30, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(annotated_frame, f"Status: {status_text}", (30, 90), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        cv2.imshow("ADAS LDW Stream Test", annotated_frame)

        # Control playback speed (25ms delay for ~40 fps playback)
        if cv2.waitKey(25) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()