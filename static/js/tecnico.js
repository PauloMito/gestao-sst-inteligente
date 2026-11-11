document.addEventListener("DOMContentLoaded", function () {
  const campoBusca = document.getElementById("buscaEmpresa");
  const botaoLimpar = document.getElementById("limparBusca");
  const contador = document.getElementById("contadorResultados");
  const mensagemVazia = document.getElementById("mensagemSemResultados");

  const linhas = Array.from(
    document.querySelectorAll(".linha-empresa")
  );

  function normalizar(texto) {
    return String(texto || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim();
  }

  function filtrarEmpresas() {
    const termo = normalizar(campoBusca.value);
    let visiveis = 0;

    linhas.forEach(function (linha) {
      const conteudo = normalizar(linha.dataset.search);
      const corresponde = conteudo.includes(termo);

      linha.hidden = !corresponde;

      if (corresponde) {
        visiveis++;
      }
    });

    contador.textContent =
      `Exibindo ${visiveis} de ${linhas.length} empresas`;

    const naoEncontrou = visiveis === 0 && linhas.length > 0;

    mensagemVazia.hidden = !naoEncontrou;
    mensagemVazia.classList.toggle("oculto", !naoEncontrou);
  }

  campoBusca.addEventListener("input", filtrarEmpresas);

  botaoLimpar.addEventListener("click", function () {
    campoBusca.value = "";
    filtrarEmpresas();
    campoBusca.focus();
  });

  document.querySelectorAll(".form-acao").forEach(function (formulario) {
    formulario.addEventListener("submit", function (evento) {
      const botao = formulario.querySelector("button");
      const textoBotao = botao.textContent.trim();

      const confirmado = window.confirm(
        `Confirma a ação "${textoBotao}" para esta empresa?`
      );

      if (!confirmado) {
        evento.preventDefault();
      }
    });
  });

  filtrarEmpresas();
})