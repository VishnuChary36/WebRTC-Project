"""
WebRTC Handler for real-time video streaming
Handles peer connections, SDP negotiation, and media streams
"""

import asyncio
import logging
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer
from aiortc.contrib.media import MediaStreamTrack
import av
import numpy as np

logger = logging.getLogger(__name__)

class WebRTCHandler:
    def __init__(self):
        # STUN servers for NAT traversal
        self.ice_servers = [
            RTCIceServer(urls=["stun:stun.l.google.com:19302"]),
            RTCIceServer(urls=["stun:stun1.l.google.com:19302"]),
        ]
        
        self.config = RTCConfiguration(iceServers=self.ice_servers)
        self.peer_connections = {}
        self.video_tracks = {}
        
        logger.info("🔗 WebRTC Handler initialized")

    async def handle_offer(self, sdp_offer, client_id=None):
        """Handle WebRTC offer and create answer"""
        if client_id is None:
            client_id = f"client_{len(self.peer_connections)}"
        
        try:
            # Create peer connection
            pc = RTCPeerConnection(configuration=self.config)
            self.peer_connections[client_id] = pc
            
            # Set up event handlers
            @pc.on("connectionstatechange")
            async def on_connectionstatechange():
                logger.info(f"🔄 Connection state changed: {pc.connectionState}")
                if pc.connectionState == "closed":
                    await self.cleanup_peer_connection(client_id)

            @pc.on("track")
            async def on_track(track):
                logger.info(f"📹 Received track: {track.kind}")
                if track.kind == "video":
                    self.video_tracks[client_id] = track
                    logger.info(f"✅ Video track registered for {client_id}")

            # Set remote description (offer)
            offer = RTCSessionDescription(sdp=sdp_offer, type="offer")
            await pc.setRemoteDescription(offer)
            
            # Create answer
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            
            logger.info(f"✅ Created WebRTC answer for {client_id}")
            return pc.localDescription.sdp
            
        except Exception as e:
            logger.error(f"❌ Error handling offer: {e}")
            raise

    async def add_ice_candidate(self, candidate_data, client_id=None):
        """Add ICE candidate to peer connection"""
        if client_id is None and self.peer_connections:
            client_id = list(self.peer_connections.keys())[0]
        
        if client_id not in self.peer_connections:
            logger.warning(f"⚠️ No peer connection found for {client_id}")
            return
        
        try:
            pc = self.peer_connections[client_id]
            
            # Handle ICE candidate data
            if isinstance(candidate_data, dict):
                # Check if candidate is not empty
                candidate_str = candidate_data.get('candidate', '')
                if not candidate_str:
                    logger.debug("Skipping empty ICE candidate")
                    return
                
                # Use aiortc's method to parse ICE candidate from SDP string
                from aiortc.sdp import candidate_from_sdp
                try:
                    candidate = candidate_from_sdp(candidate_str)
                    candidate.sdpMid = candidate_data.get('sdpMid')
                    candidate.sdpMLineIndex = candidate_data.get('sdpMLineIndex')
                except Exception as parse_error:
                    logger.warning(f"Could not parse ICE candidate: {parse_error}")
                    return
            else:
                candidate = candidate_data
            
            await pc.addIceCandidate(candidate)
            logger.debug(f"🧊 Added ICE candidate for {client_id}")
        except Exception as e:
            logger.error(f"❌ Error adding ICE candidate: {e}")
            logger.debug(f"Candidate data: {candidate_data}")

    async def get_video_frame(self, client_id=None):
        """Get latest video frame from client"""
        if client_id is None and self.video_tracks:
            client_id = list(self.video_tracks.keys())[0]
        
        if client_id not in self.video_tracks:
            return None
        
        try:
            track = self.video_tracks[client_id]
            frame = await track.recv()
            
            # Convert to numpy array
            img = frame.to_ndarray(format="rgb24")
            return img
            
        except Exception as e:
            logger.error(f"❌ Error getting video frame: {e}")
            return None

    async def cleanup_peer_connection(self, client_id):
        """Clean up peer connection and related resources"""
        try:
            if client_id in self.peer_connections:
                pc = self.peer_connections[client_id]
                await pc.close()
                del self.peer_connections[client_id]
                logger.info(f"🧹 Cleaned up peer connection for {client_id}")
            
            if client_id in self.video_tracks:
                del self.video_tracks[client_id]
                logger.info(f"🧹 Cleaned up video track for {client_id}")
                
        except Exception as e:
            logger.error(f"❌ Error cleaning up peer connection: {e}")

    async def close_all_connections(self):
        """Close all peer connections"""
        for client_id in list(self.peer_connections.keys()):
            await self.cleanup_peer_connection(client_id)
        
        logger.info("🛑 All peer connections closed")

    def get_connection_stats(self):
        """Get statistics for all connections"""
        stats = {
            "total_connections": len(self.peer_connections),
            "active_video_tracks": len(self.video_tracks),
            "connections": {}
        }
        
        for client_id, pc in self.peer_connections.items():
            stats["connections"][client_id] = {
                "state": pc.connectionState,
                "ice_connection_state": pc.iceConnectionState,
                "ice_gathering_state": pc.iceGatheringState
            }
        
        return stats