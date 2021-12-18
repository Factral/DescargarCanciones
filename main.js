
const resultados = document.querySelector('#results')
const spinner = document.querySelector('.loader')
const input = document.getElementById('Buscador')

const posicionesIndexadas = []
const urls = []

function creartabla (tamaño = true) {
  const tbl = document.createElement('table')
  tbl.setAttribute('id', 'tabla')

  const table = tamaño
    ? '<thead> <tr> <th>#</th> <th>Album</th> <th>Cancion</th> <th>Artista</th> <th>Tamaño</th> <th></th> </tr> </thead> <tbody></tbody>'
    : '<thead> <tr> <th>#</th> <th>Album</th> <th>Cancion</th> <th>Artista</th> <th></th> </tr> </thead><tbody></tbody>'
  tbl.innerHTML += table

  resultados.appendChild(tbl)
  return tbl
}

// debounce function
function debounce (callback, wait) {
  let timeout
  return (...args) => {
    clearTimeout(timeout)
    timeout = setTimeout(function () { callback.apply(this, args) }, wait)
  }
}

function organizarCanciones (song, size) {
  if (!document.getElementById('tabla')) {
    creartabla()
  }

  if (!document.getElementById('descarga')) {
    const descargarTodos = document.createElement('a')
    descargarTodos.id = 'descarga'
    resultados.prepend(descargarTodos)
  }

  posicionesIndexadas.push(song.position)
  document.getElementById('descarga').innerText = `${posicionesIndexadas.length}/${size} canciones`
  const tbodyRef = document.getElementById('tabla').getElementsByTagName('tbody')[0]

  const data = `
              <td>${song.position}</td>
              <td><a id="external_link" href="${song.external_link}" target="_blank"><img loading="lazy" src="${song.metadata.cover}" class="cover"></a></td>
              <td>${song.metadata.name}</td>
              <td>${song.metadata.artist}</td>
              <td>${song['tamaño']}</td>
              <td><a href='${song.link}' download'>Descargar</a></td>
              `

  let a = 99999; let posMasCercana
  for (let i = 0; i < posicionesIndexadas.length; i += 1) {
    if (song.position < posicionesIndexadas[i]) {
      posMasCercana = Math.min(a, posicionesIndexadas[i])
      a = posMasCercana
    }
  }

  if (a !== 99999) {
    const d1 = document.querySelector(`.n${posMasCercana}`)
    d1.insertAdjacentHTML('beforebegin', `<tr class="song n${song.position}">${data}</tr>`)
  }

  if (a === 99999 || posicionesIndexadas.length < 0) {
    const newRow = tbodyRef.insertRow()
    newRow.setAttribute('class', `song n${song.position}`)
    newRow.innerHTML += data
  }

  urls.push({ link: song.link, nombre: song.metadata.name })

  spinner.classList.add('hidden')

  if (posicionesIndexadas.length === size) {
    document.getElementById('descarga').innerHTML = '<a id="generateZip" href="#">generar zip de las canciones</a>'
  }
}

function generarzip () {
  const zip = new JSZip()
  const carpeta = zip.folder('canciones')

  let count = 0

  urls.forEach((url) => {
    JSZipUtils.getBinaryContent(url.link, (err, dataCancion) => {
      if (err) {
        throw err
      }
      carpeta.file(`${url.nombre}.mp3`, dataCancion, { binary: true })
      count += 1

      if (count === urls.length) {
        zip.generateAsync({ type: 'blob' }).then((content) => {
          const linkZip = URL.createObjectURL(content)
          document.getElementById('descarga').href = linkZip
          document.getElementById('descarga').download = 'canciones.zip'
          document.getElementById('descarga').innerText = 'Completado'
          document.getElementById('descarga').className = 'disabled'
          document.getElementById('descarga').click()
        })
      }
    })
  })
}

input.addEventListener('keyup', debounce(() => {
  if (input.value.length > 1) {
    input.blur()
    if (document.getElementById('error')) {
      document.getElementById('error').remove()
    }
    if (document.getElementById('tabla')) {
      document.getElementById('tabla').remove()
    }
    spinner.classList.remove('hidden')
    document.getElementById('explicacion').style.display = 'none'

    if (input.value.startsWith('https://open.spotify.com/playlist')) {
      const canciones = []
      console.log(canciones)
      fetch(`https://buscar-canciones.herokuapp.com/v1/playlist?link=${input.value}`)
        .then((response) => response.json())
        .then((list) => {
          Object.entries(list.canciones).forEach((track) => {
            canciones.push({
              position: Number(track[0]) + 1,
              metadata: track[1]
            })
          })

          const data_to_send = {
            playlist: input.value,
            songs: canciones
          }
          console.log(data_to_send)
          const socket = io('https://buscar-canciones.herokuapp.com/', { transports: ['websocket'], upgrade: false })

          socket.emit('message', data_to_send)

          // handle the event sent with socket.send()
          socket.on('disconnect', () => {
            socket.disconnect()
          })

          socket.on('message_reply', (data) => {
            organizarCanciones(data, canciones.length)
            spinner.classList.add('hidden')
          })
        })
    } else {
      fetch(
        `https://buscar-canciones.herokuapp.com/v1/search/song?name=${encodeURIComponent(input.value).replaceAll('%20', '+')}`
      )
        .then((response) => response.json())
        .then((song) => {
          if (Object.keys(song).length === 0) {
            const content = document.createElement('p')
            content.id = 'error'
            content.innerText = 'no se encontro la cancion :('
            resultados.prepend(content)
          }
          else {

            if (!document.getElementById('tabla')) {
              creartabla(false)
            }
 
            // crea la linea para la cancion
            const tbodyRef = document.getElementById('tabla').getElementsByTagName('tbody')[0]
            tbodyRef.innerHTML = ''

            if(input.value.startsWith('https://www.youtube.com')){
              const newRow = tbodyRef.insertRow()
              newRow.setAttribute('class', `song 1`)
              newRow.innerHTML += `
              <td>1</td>
              <td><a id="external_link" href="${song.external_link}" target="_blank"><img loading="lazy" src="${song.cover}" class="cover"></a></td>
              <td class="songName">${song.nombre}</td>
              <td>${song.artista}</td>
              <td><a class="generateLink" value='${song.uri}' href='*-*'>Descarga</a></td>`
            }
            else{  

            Object.entries(song).forEach(([position, track]) => {
              const newRow = tbodyRef.insertRow()
              newRow.setAttribute('class', `song ${Number(position) + 1}`)

              newRow.innerHTML += `
              <td>${Number(position) + 1}</td>
              <td><a id="external_link" href="${track.external_link}" target="_blank"><img loading="lazy" src="${track.cover}" class="cover"></a></td>
              <td class="songName">${track.nombre}</td>
              <td>${track.artista}</td>
              <td><a class="generateLink" value='${track.uri}' href='*-*'>Descarga</a></td>`
            })
          }
        }
          spinner.classList.add('hidden')
        })
    }
  }
}, 800))

document.addEventListener('click', (e) => {
  if (e.target && e.target.classList[0] === 'generateLink') {
    e.preventDefault()
    e.target.innerText = 'Generando link...'
    fetch(`https://buscar-canciones.herokuapp.com/v1/song?name=${encodeURIComponent(e.target.attributes.value.nodeValue)}`)
      .then((response) => response.json())
      .then((song) => {
        e.target.href = song.link
        e.target.setAttribute('class', 'disabled')
        e.target.click()
        e.target.innerText = 'Descargado'
      })
  }
  if (e.target && e.target.id === 'generateZip') {
    e.preventDefault()
    e.target.innerText = 'Generando link...'
    generarzip()
  }
})
