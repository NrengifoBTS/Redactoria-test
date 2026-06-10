// Catálogo de dominios destino por marca, para la creación de proyectos (LP).
// Fuente: tablas oficiales VJS / MCR. La clave coincide con `proyecto`/`proyectoFilter`
// (viajemos | mcr). Cada entrada: dominio canónico, URL, país/propósito e idiomas.
//
// Si cambian los dominios, este es el único lugar a editar.

export const DOMINIOS = {
  viajemos: [
    { dominio: "viajemos.com", url: "https://www.viajemos.com", pais: ".com (Global)", idiomas: ["ES", "EN", "PT"] },
    { dominio: "viajemos.mx", url: "https://www.viajemos.mx", pais: "México", idiomas: ["ES", "EN"] },
    { dominio: "es.viajemos.com", url: "https://es.viajemos.com", pais: "España", idiomas: ["ES", "EN"] },
    { dominio: "viajemos.com.pr", url: "https://www.viajemos.com.pr", pais: "Puerto Rico", idiomas: ["ES", "EN"] },
    { dominio: "viajemos.com.co", url: "https://www.viajemos.com.co", pais: "Colombia", idiomas: ["ES", "EN"] },
    { dominio: "viajemos.com.ve", url: "https://www.viajemos.com.ve", pais: "Venezuela", idiomas: ["ES", "EN"] },
    { dominio: "viajemos.com.br", url: "https://www.viajemos.com.br", pais: "Brasil", idiomas: ["EN", "PT"] },
    { dominio: "viajemos.com.pt", url: "https://www.viajemos.com.pt", pais: "Portugal", idiomas: ["EN", "PT"] },
    { dominio: "viajemos.com.ec", url: "https://www.viajemos.com.ec", pais: "Ecuador", idiomas: ["ES", "EN"] },
    { dominio: "viajemos.com.ar", url: "https://www.viajemos.com.ar", pais: "Argentina", idiomas: ["ES", "EN"] },
    { dominio: "cl.viajemos.com", url: "https://cl.viajemos.com", pais: "Chile", idiomas: ["ES", "EN"] },
    { dominio: "viajemos.cr", url: "https://www.viajemos.cr", pais: "Costa Rica", idiomas: ["ES", "EN"] },
    { dominio: "viajemos.com.bo", url: "https://www.viajemos.com.bo", pais: "Bolivia", idiomas: ["ES", "EN"] },
    { dominio: "viajemos.com.do", url: "https://www.viajemos.com.do", pais: "República Dominicana", idiomas: ["ES", "EN"] },
    { dominio: "viajemos.com.gt", url: "https://www.viajemos.com.gt", pais: "Guatemala", idiomas: ["ES", "EN"] },
    { dominio: "viajemos.com.hn", url: "https://www.viajemos.com.hn", pais: "Honduras", idiomas: ["ES", "EN"] },
    { dominio: "viajemos.com.ni", url: "https://www.viajemos.com.ni", pais: "Nicaragua", idiomas: ["ES", "EN"] },
    { dominio: "viajemos.com.pa", url: "https://www.viajemos.com.pa", pais: "Panamá", idiomas: ["ES", "EN"] },
    { dominio: "uy.viajemos.com", url: "https://uy.viajemos.com", pais: "Uruguay", idiomas: ["ES", "EN"] },
    { dominio: "viajemos.com.py", url: "https://www.viajemos.com.py", pais: "Paraguay", idiomas: ["ES", "EN"] },
    { dominio: "viajemos.com.sv", url: "https://www.viajemos.com.sv", pais: "Salvador", idiomas: ["ES", "EN"] },
    { dominio: "viajemos.com.pe", url: "https://www.viajemos.com.pe", pais: "Perú", idiomas: ["ES", "EN"] },
    { dominio: "viajemos.ca", url: "https://www.viajemos.ca", pais: "Canadá", idiomas: ["EN"] },
    { dominio: "viajemos.co.uk", url: "https://www.viajemos.co.uk", pais: "Reino Unido", idiomas: ["EN"] },
  ],
  mcr: [
    { dominio: "milescarrental.co.uk", url: "https://www.milescarrental.co.uk", pais: "Reino Unido", idiomas: ["EN"] },
    { dominio: "milescarrental.com", url: "https://www.milescarrental.com", pais: ".com (Global / Estados Unidos)", idiomas: ["ES", "EN", "PT"] },
    { dominio: "milescarrental.com.br", url: "https://www.milescarrental.com.br", pais: "Brasil", idiomas: ["EN", "PT"] },
    { dominio: "milescarrental.com.es", url: "https://www.milescarrental.com.es", pais: "España", idiomas: ["ES", "EN"] },
    { dominio: "milescarrentalatlanta.com", url: "https://www.milescarrentalatlanta.com", pais: "Atlanta", idiomas: ["ES", "EN", "PT"] },
    { dominio: "milescarrentaldallas.com", url: "https://www.milescarrentaldallas.com", pais: "Dallas", idiomas: ["ES", "EN", "PT"] },
    { dominio: "milescarrental.eu", url: "https://www.milescarrental.eu", pais: "Europa", idiomas: ["ES", "EN", "PT"] },
    { dominio: "milescarrentalfortlauderdale.com", url: "https://www.milescarrentalfortlauderdale.com", pais: "Fort Lauderdale", idiomas: ["ES", "EN", "PT"] },
    { dominio: "milescarrentalhouston.com", url: "https://www.milescarrentalhouston.com", pais: "Houston", idiomas: ["ES", "EN", "PT"] },
    { dominio: "milescarrentallasvegas.com", url: "https://www.milescarrentallasvegas.com", pais: "Las Vegas", idiomas: ["ES", "EN", "PT"] },
    { dominio: "milescarrentallosangeles.com", url: "https://www.milescarrentallosangeles.com", pais: "Los Ángeles", idiomas: ["ES", "EN", "PT"] },
    { dominio: "milescarrentalmiami.com", url: "https://www.milescarrentalmiami.com", pais: "Miami", idiomas: ["ES", "EN", "PT"] },
    { dominio: "milescarrentalnewyork.com", url: "https://www.milescarrentalnewyork.com", pais: "Nueva York", idiomas: ["ES", "EN", "PT"] },
    { dominio: "milescarrentalorlando.com", url: "https://www.milescarrentalorlando.com", pais: "Orlando", idiomas: ["ES", "EN", "PT"] },
    { dominio: "milescarrentalpalmbeach.com", url: "https://www.milescarrentalpalmbeach.com", pais: "Palm Beach", idiomas: ["ES", "EN", "PT"] },
    { dominio: "milescarrentalsandiego.com", url: "https://www.milescarrentalsandiego.com", pais: "San Diego", idiomas: ["ES", "EN", "PT"] },
    { dominio: "milescarrentalsanfrancisco.com", url: "https://www.milescarrentalsanfrancisco.com", pais: "San Francisco", idiomas: ["ES", "EN", "PT"] },
    { dominio: "milescarrentaltampa.com", url: "https://www.milescarrentaltampa.com", pais: "Tampa", idiomas: ["ES", "EN", "PT"] },
    { dominio: "milescarrental.com.mx", url: "https://www.milescarrental.com.mx", pais: "México", idiomas: ["ES", "EN"] },
    { dominio: "milescarrental.de", url: "https://www.milescarrental.de", pais: "Alemania", idiomas: ["EN"] },
    { dominio: "milescarrental.fr", url: "https://www.milescarrental.fr", pais: "Francia", idiomas: ["EN"] },
    { dominio: "milescarrental.it", url: "https://www.milescarrental.it", pais: "Italia", idiomas: ["EN"] },
    { dominio: "milescarrental.pt", url: "https://www.milescarrental.pt", pais: "Portugal", idiomas: ["EN", "PT"] },
  ],
};

// Devuelve la lista de dominios para una marca (key proyecto/proyectoFilter).
export const getDominiosPorMarca = (marca) => DOMINIOS[marca] || [];
