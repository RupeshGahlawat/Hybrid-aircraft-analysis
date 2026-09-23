import React, { useRef, useEffect } from 'react';
import * as THREE from 'three';

/**
 * Procedural ATR-72 Regional Turboprop Builder for Three.js.
 * Produces clean aerospace-grade geometry with:
 * - High-wing with twin engine nacelles & electric cyan trim rings
 * - 6-blade composite propellers with spinning motion blur disks
 * - T-tail vertical fin & horizontal stabilizer
 * - Fuselage sponsons with retractable landing gear
 */
function buildATR72Model(isHybrid = true) {
  const root = new THREE.Group();

  // Premium Off-White Aerospace PBR Materials
  const bodyMaterial = new THREE.MeshStandardMaterial({
    color: isHybrid ? 0xFFFFFF : 0xF1F5F9,
    metalness: 0.12,
    roughness: 0.35,
  });

  const deiceMaterial = new THREE.MeshStandardMaterial({
    color: 0x64748B, // Slate silver leading edge de-ice boots
    metalness: 0.75,
    roughness: 0.25,
  });

  const accentMaterial = new THREE.MeshStandardMaterial({
    color: isHybrid ? 0x0284C7 : 0x475569, // Electric Cyan vs Conventional Slate
    metalness: 0.3,
    roughness: 0.3,
  });

  const glassMaterial = new THREE.MeshPhysicalMaterial({
    color: 0x0F172A,
    metalness: 0.9,
    roughness: 0.1,
    transmission: 0.4,
    transparent: true,
    opacity: 0.85,
  });

  const propMaterial = new THREE.MeshStandardMaterial({
    color: 0x1E293B,
    metalness: 0.4,
    roughness: 0.3,
  });

  const propDiskMaterial = new THREE.MeshBasicMaterial({
    color: isHybrid ? 0x38BDF8 : 0x94A3B8,
    transparent: true,
    opacity: 0.35,
    side: THREE.DoubleSide,
  });

  // 1. Fuselage
  const nose = new THREE.Mesh(new THREE.ConeGeometry(0.9, 2.2, 32), bodyMaterial);
  nose.rotation.x = Math.PI / 2;
  nose.position.z = 6.0;
  root.add(nose);

  const cabin = new THREE.Mesh(new THREE.CylinderGeometry(0.9, 0.9, 10.5, 32), bodyMaterial);
  cabin.rotation.x = Math.PI / 2;
  cabin.position.z = 0.0;
  root.add(cabin);

  const windshield = new THREE.Mesh(
    new THREE.CylinderGeometry(0.91, 0.91, 1.4, 16, 1, false, 0, Math.PI),
    glassMaterial
  );
  windshield.rotation.x = Math.PI / 2;
  windshield.rotation.z = Math.PI;
  windshield.position.set(0, 0.12, 4.6);
  root.add(windshield);

  const tail = new THREE.Mesh(new THREE.ConeGeometry(0.9, 3.8, 32), bodyMaterial);
  tail.rotation.x = -Math.PI / 2;
  tail.position.set(0, 0.28, -7.0);
  root.add(tail);

  // 2. High Wing
  const wing = new THREE.Mesh(new THREE.BoxGeometry(14.2, 0.16, 1.8), bodyMaterial);
  wing.position.set(0, 0.95, 0.6);
  root.add(wing);

  const wingEdge = new THREE.Mesh(new THREE.BoxGeometry(14.2, 0.17, 0.18), deiceMaterial);
  wingEdge.position.set(0, 0.95, 1.5);
  root.add(wingEdge);

  [-7.1, 7.1].forEach((x) => {
    const tip = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.6, 0.7), accentMaterial);
    tip.position.set(x, 0.95, 0.6);
    root.add(tip);
  });

  // 3. T-Tail
  const fin = new THREE.Mesh(new THREE.BoxGeometry(0.14, 2.9, 2.2), bodyMaterial);
  fin.position.set(0, 2.4, -6.6);
  fin.rotation.x = -0.32;
  root.add(fin);

  const hStab = new THREE.Mesh(new THREE.BoxGeometry(5.2, 0.12, 1.1), bodyMaterial);
  hStab.position.set(0, 3.8, -7.2);
  root.add(hStab);

  // 4. Twin Turboprop Nacelles & Propellers
  const propellers = [];
  const propDisks = [];

  [-2.8, 2.8].forEach((xPos) => {
    const nacelle = new THREE.Mesh(new THREE.CylinderGeometry(0.46, 0.5, 3.6, 24), bodyMaterial);
    nacelle.rotation.x = Math.PI / 2;
    nacelle.position.set(xPos, 0.68, 0.6);
    root.add(nacelle);

    const accentRing = new THREE.Mesh(new THREE.TorusGeometry(0.48, 0.06, 16, 32), accentMaterial);
    accentRing.position.set(xPos, 0.68, 2.1);
    root.add(accentRing);

    const propHubGroup = new THREE.Group();
    propHubGroup.position.set(xPos, 0.68, 2.45);

    const spinner = new THREE.Mesh(new THREE.ConeGeometry(0.26, 0.65, 20), deiceMaterial);
    spinner.rotation.x = Math.PI / 2;
    propHubGroup.add(spinner);

    for (let b = 0; b < 6; b++) {
      const angle = (b * Math.PI) / 3;
      const blade = new THREE.Mesh(new THREE.BoxGeometry(0.09, 1.85, 0.04), propMaterial);
      blade.position.set(Math.cos(angle) * 0.92, Math.sin(angle) * 0.92, -0.05);
      blade.rotation.z = angle;
      blade.rotation.x = 0.28;
      propHubGroup.add(blade);
    }
    root.add(propHubGroup);
    propellers.push(propHubGroup);

    const disk = new THREE.Mesh(new THREE.CircleGeometry(2.0, 32), propDiskMaterial);
    disk.position.set(xPos, 0.68, 2.42);
    root.add(disk);
    propDisks.push(disk);
  });

  // 5. Landing Gear
  const sponson = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.55, 2.8), bodyMaterial);
  sponson.position.set(0, -0.68, 0.3);
  root.add(sponson);

  const gearGroup = new THREE.Group();
  const noseStrut = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.9), deiceMaterial);
  noseStrut.position.set(0, -1.05, 4.8);
  const noseWheel = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.2, 0.14, 16), propMaterial);
  noseWheel.rotation.z = Math.PI / 2;
  noseWheel.position.set(0, -1.45, 4.8);
  gearGroup.add(noseStrut, noseWheel);

  [-1.0, 1.0].forEach((x) => {
    const strut = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 0.8), deiceMaterial);
    strut.position.set(x, -0.95, 0.3);
    const w1 = new THREE.Mesh(new THREE.CylinderGeometry(0.26, 0.26, 0.16, 16), propMaterial);
    w1.rotation.z = Math.PI / 2;
    w1.position.set(x - 0.14, -1.35, 0.3);
    const w2 = new THREE.Mesh(new THREE.CylinderGeometry(0.26, 0.26, 0.16, 16), propMaterial);
    w2.rotation.z = Math.PI / 2;
    w2.position.set(x + 0.14, -1.35, 0.3);
    gearGroup.add(strut, w1, w2);
  });
  root.add(gearGroup);

  return { root, propellers, propDisks, gearGroup };
}

export default function AviationScene3D({
  currentTelemetry,
  convTelemetry,
  cameraMode = 'chase',
  isDualMode = true,
}) {
  const containerRef = useRef(null);
  const stateRef = useRef({
    hybridModel: null,
    convModel: null,
    camera: null,
    scene: null,
    renderer: null,
    propAngle: 0,
    // Smooth LERP Target States
    hybridTargetPos: new THREE.Vector3(0, 1.5, -700),
    hybridCurrentPos: new THREE.Vector3(0, 1.5, -700),
    hybridTargetPitch: 0,
    hybridCurrentPitch: 0,

    convTargetPos: new THREE.Vector3(-16, 1.5, -700),
    convCurrentPos: new THREE.Vector3(-16, 1.5, -700),
    convTargetPitch: 0,
    convCurrentPitch: 0,

    cameraTargetPos: new THREE.Vector3(14, 7.5, -722),
    cameraCurrentPos: new THREE.Vector3(14, 7.5, -722),
    cameraLookAtTarget: new THREE.Vector3(0, 3, -694),
    cameraLookAtCurrent: new THREE.Vector3(0, 3, -694),

    // Orbit Controls
    isDragging: false,
    prevMouseX: 0,
    prevMouseY: 0,
    orbitAzimuth: 0.35,
    orbitElevation: 0.28,
    orbitDistance: 28,
  });

  // 1. Initialize Scene & Renderer
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 560;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xEDF2F7);
    scene.fog = new THREE.FogExp2(0xEDF2F7, 0.0016);
    stateRef.current.scene = scene;

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.5, 4000);
    camera.position.set(14, 7.5, -722);
    stateRef.current.camera = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);
    stateRef.current.renderer = renderer;

    // Aerospace Lighting
    const ambientLight = new THREE.HemisphereLight(0xFFFFFF, 0xCBD5E1, 0.95);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xFFFFFF, 1.5);
    sunLight.position.set(80, 160, 100);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 10;
    sunLight.shadow.camera.far = 500;
    const d = 70;
    sunLight.shadow.camera.left = -d;
    sunLight.shadow.camera.right = d;
    sunLight.shadow.camera.top = d;
    sunLight.shadow.camera.bottom = -d;
    scene.add(sunLight);

    // PBR Runway
    const runwayGroup = new THREE.Group();
    const asphalt = new THREE.Mesh(
      new THREE.PlaneGeometry(42, 2600),
      new THREE.MeshStandardMaterial({ color: 0x1E293B, roughness: 0.85, metalness: 0.1 })
    );
    asphalt.rotation.x = -Math.PI / 2;
    asphalt.receiveShadow = true;
    runwayGroup.add(asphalt);

    // Centerline Markings
    const lineMat = new THREE.MeshBasicMaterial({ color: 0xFFFFFF });
    for (let z = -1200; z < 1200; z += 32) {
      const line = new THREE.Mesh(new THREE.PlaneGeometry(1.4, 20), lineMat);
      line.rotation.x = -Math.PI / 2;
      line.position.set(0, 0.03, z);
      runwayGroup.add(line);
    }

    // Touchdown markings
    [-12, 12].forEach((x) => {
      for (let z = -850; z < -300; z += 45) {
        const td = new THREE.Mesh(new THREE.PlaneGeometry(3.2, 22), lineMat);
        td.rotation.x = -Math.PI / 2;
        td.position.set(x, 0.03, z);
        runwayGroup.add(td);
      }
    });

    // Runway Edge Lights
    const lampMat = new THREE.MeshBasicMaterial({ color: 0xFEF08A });
    for (let z = -1250; z < 1250; z += 50) {
      [-21.5, 21.5].forEach((x) => {
        const lamp = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 0.4), lampMat);
        lamp.position.set(x, 0.2, z);
        runwayGroup.add(lamp);
      });
    }

    // Ground Airfield Landscape
    const terrain = new THREE.Mesh(
      new THREE.PlaneGeometry(2600, 3200),
      new THREE.MeshStandardMaterial({ color: 0xE2E8F0, roughness: 0.95 })
    );
    terrain.rotation.x = -Math.PI / 2;
    terrain.position.y = -0.05;
    terrain.receiveShadow = true;
    runwayGroup.add(terrain);

    scene.add(runwayGroup);

    // Build Aircraft
    const hybrid = buildATR72Model(true);
    hybrid.root.position.set(0, 1.5, -700);
    scene.add(hybrid.root);
    stateRef.current.hybridModel = hybrid;

    const conv = buildATR72Model(false);
    conv.root.position.set(-16, 1.5, -700);
    conv.root.visible = isDualMode;
    scene.add(conv.root);
    stateRef.current.convModel = conv;

    // Continuous 60 FPS Animation & LERP Smoothing Loop
    let animId;
    const animate = () => {
      animId = requestAnimationFrame(animate);
      const s = stateRef.current;

      // Spin Propellers smoothly
      s.propAngle += 0.5;
      if (s.hybridModel) {
        s.hybridModel.propellers.forEach((p) => (p.rotation.z = s.propAngle));
      }
      if (s.convModel && s.convModel.root.visible) {
        s.convModel.propellers.forEach((p) => (p.rotation.z = s.propAngle));
      }

      // Smooth Position and Rotation LERP (Interpolation Factor 0.08)
      if (s.hybridModel) {
        s.hybridCurrentPos.lerp(s.hybridTargetPos, 0.08);
        s.hybridCurrentPitch = THREE.MathUtils.lerp(s.hybridCurrentPitch, s.hybridTargetPitch, 0.08);

        s.hybridModel.root.position.copy(s.hybridCurrentPos);
        s.hybridModel.root.rotation.x = THREE.MathUtils.degToRad(-s.hybridCurrentPitch);
      }

      if (s.convModel && s.convModel.root.visible) {
        s.convCurrentPos.lerp(s.convTargetPos, 0.08);
        s.convCurrentPitch = THREE.MathUtils.lerp(s.convCurrentPitch, s.convTargetPitch, 0.08);

        s.convModel.root.position.copy(s.convCurrentPos);
        s.convModel.root.rotation.x = THREE.MathUtils.degToRad(-s.convCurrentPitch);
      }

      // Camera Smooth LERP
      if (cameraMode === 'orbit') {
        const target = s.hybridCurrentPos;
        const x = target.x + s.orbitDistance * Math.cos(s.orbitElevation) * Math.sin(s.orbitAzimuth);
        const y = target.y + s.orbitDistance * Math.sin(s.orbitElevation) + 2;
        const z = target.z + s.orbitDistance * Math.cos(s.orbitElevation) * Math.cos(s.orbitAzimuth);
        camera.position.set(x, y, z);
        camera.lookAt(target.x, target.y + 1.5, target.z);
      } else {
        s.cameraCurrentPos.lerp(s.cameraTargetPos, 0.08);
        s.cameraLookAtCurrent.lerp(s.cameraLookAtTarget, 0.08);

        camera.position.copy(s.cameraCurrentPos);
        camera.lookAt(s.cameraLookAtCurrent);
      }

      renderer.render(scene, camera);
    };
    animate();

    // Mouse Drag Listeners for Interactive Orbit Mode
    const onMouseDown = (e) => {
      s.isDragging = true;
      s.prevMouseX = e.clientX;
      s.prevMouseY = e.clientY;
    };
    const onMouseMove = (e) => {
      if (!s.isDragging) return;
      const deltaX = e.clientX - s.prevMouseX;
      const deltaY = e.clientY - s.prevMouseY;
      s.orbitAzimuth -= deltaX * 0.008;
      s.orbitElevation = Math.max(0.05, Math.min(1.4, s.orbitElevation + deltaY * 0.008));
      s.prevMouseX = e.clientX;
      s.prevMouseY = e.clientY;
    };
    const onMouseUp = () => {
      s.isDragging = false;
    };
    const dom = renderer.domElement;
    dom.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);

    // Resize Observer
    const resizeObserver = new ResizeObserver(() => {
      if (!container || !renderer || !camera) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      if (w > 0 && h > 0) {
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
      }
    });
    resizeObserver.observe(container);

    return () => {
      cancelAnimationFrame(animId);
      resizeObserver.disconnect();
      dom.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      renderer.dispose();
      container.innerHTML = '';
    };
  }, []);

  // 2. Set LERP Targets when Telemetry updates
  useEffect(() => {
    const s = stateRef.current;
    if (!s.hybridModel) return;

    const altFt = currentTelemetry?.altitude_ft || 0;
    const pitchDeg = currentTelemetry?.pitch_deg || 0;
    const distanceKm = currentTelemetry?.distance_km || 0;
    const phase = currentTelemetry?.phase || 'takeoff';
    const speed = currentTelemetry?.airspeed_kt || 0;

    // Calculate Target Z and Y
    const zPos = -700 + Math.min(distanceKm * 400, 1100);
    let yPos = 1.5;
    if (phase !== 'takeoff') {
      yPos = 1.5 + Math.min(altFt / 180.0, 75.0);
    }

    s.hybridTargetPos.set(0, yPos, zPos);
    s.hybridTargetPitch = pitchDeg;

    // Retract Gear
    const isGearDown = currentTelemetry?.gear_extended ?? (altFt < 350);
    s.hybridModel.gearGroup.visible = isGearDown;

    const blurOpacity = speed > 25 ? 0.35 : 0.08;
    s.hybridModel.propDisks.forEach((d) => (d.material.opacity = blurOpacity));

    // Conventional Ghost Target
    if (s.convModel) {
      s.convModel.root.visible = isDualMode;
      if (isDualMode && convTelemetry) {
        const convDist = convTelemetry.distance_km || 0;
        const convAlt = convTelemetry.altitude_ft || 0;
        const convPitch = convTelemetry.pitch_deg || 0;
        const convPhase = convTelemetry.phase || 'takeoff';
        const convZ = -700 + Math.min(convDist * 400, 1100);
        let convY = 1.5;
        if (convPhase !== 'takeoff') {
          convY = 1.5 + Math.min(convAlt / 180.0, 75.0);
        }
        s.convTargetPos.set(-16, convY, convZ);
        s.convTargetPitch = convPitch;
        s.convModel.gearGroup.visible = convTelemetry.gear_extended ?? (convAlt < 350);
      }
    }

    // Camera Mode Targets
    if (cameraMode === 'chase') {
      // Third-person quarter view
      s.cameraTargetPos.set(s.hybridTargetPos.x + 14, s.hybridTargetPos.y + 6.0, s.hybridTargetPos.z - 22);
      s.cameraLookAtTarget.set(s.hybridTargetPos.x, s.hybridTargetPos.y + 1.5, s.hybridTargetPos.z + 4);
    } else if (cameraMode === 'tower') {
      // Runway Tower View
      s.cameraTargetPos.set(32, 4.0, -500);
      s.cameraLookAtTarget.set(s.hybridTargetPos.x, s.hybridTargetPos.y + 1.0, s.hybridTargetPos.z);
    } else if (cameraMode === 'cockpit') {
      // Cockpit View
      s.cameraTargetPos.set(s.hybridTargetPos.x, s.hybridTargetPos.y + 1.0, s.hybridTargetPos.z + 5.0);
      s.cameraLookAtTarget.set(s.hybridTargetPos.x, s.hybridTargetPos.y + 1.0, s.hybridTargetPos.z + 80);
    }
  }, [currentTelemetry, convTelemetry, cameraMode, isDualMode]);

  return (
    <div
      className="scene-canvas-wrapper"
      ref={containerRef}
      style={{ cursor: cameraMode === 'orbit' ? 'grab' : 'default' }}
      title={cameraMode === 'orbit' ? 'Drag with mouse to rotate 3D view' : ''}
    />
  );
}
